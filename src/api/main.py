"""FastAPI application - REST API for the video generator."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from src.core.config import Config
from src.pipeline.orchestrator import Pipeline, Job
from src.modules.story.generator import StoryGenerator
from src.modules.scene.generator import RuleBasedSceneGenerator, OllamaSceneGenerator
from src.modules.image.generator import DummyImageGenerator
from src.modules.tts.engine import DummyTTSEngine
from src.modules.animation.animator import FFmpegAnimator
from src.modules.video.composer import FFmpegComposer
from src.modules.video.subtitles import SubtitleGenerator
from src.modules.storage.local import LocalStorage


# In-memory job store (replace with Redis in production)
jobs: dict[str, Job] = {}
config = Config()
pipeline: Optional[Pipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    config.ensure_dirs()
    pipeline = _build_pipeline(config)
    yield


app = FastAPI(title="AI Cartoon Video Generator", version="2.0.0", lifespan=lifespan)


def _build_pipeline(cfg: Config) -> Pipeline:
    """Factory: builds pipeline with configured modules."""
    scene_gen = (OllamaSceneGenerator(cfg.llm_model)
                 if cfg.scene_generator == "llm" else RuleBasedSceneGenerator())

    try:
        import torch
        if torch.cuda.is_available():
            from src.modules.image.generator import StableDiffusionGenerator
            image_gen = StableDiffusionGenerator(cfg)
        else:
            image_gen = DummyImageGenerator(cfg)
    except ImportError:
        image_gen = DummyImageGenerator(cfg)

    # Story generator (requires Ollama running)
    story_gen = StoryGenerator(model=cfg.llm_model)

    tts_engine = DummyTTSEngine(cfg)
    animator = FFmpegAnimator(cfg)
    composer = FFmpegComposer(cfg)
    subtitle_gen = SubtitleGenerator()
    storage = LocalStorage(cfg)

    return Pipeline(scene_gen, image_gen, tts_engine, animator, composer, storage,
                    story_gen=story_gen, subtitle_gen=subtitle_gen)


# --- Request/Response Models ---

class GenerateRequest(BaseModel):
    story: Optional[str] = None           # Full story text OR...
    idea: Optional[str] = None            # Brief idea (LLM generates story)
    style: str = "cartoon"                # cartoon, anime, pixar, comic
    content_type: str = "cartoon"         # cartoon, motivation, funny, horror, educational
    subtitles: bool = True


class GenerateResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    output_path: Optional[str] = None
    error: Optional[str] = None
    scenes_count: int = 0


# --- Endpoints ---

@app.post("/generate", response_model=GenerateResponse)
async def generate_video(req: GenerateRequest, background_tasks: BackgroundTasks):
    """Submit a story or idea for video generation."""
    if not req.story and not req.idea:
        raise HTTPException(status_code=400, detail="Provide either 'story' or 'idea'")

    job = Job(
        story=req.story or "",
        idea=req.idea or "",
        style=req.style,
        content_type=req.content_type,
        subtitles=req.subtitles,
    )
    jobs[job.id] = job
    background_tasks.add_task(_run_pipeline, job)

    return GenerateResponse(job_id=job.id, status=job.status.value, message="Video generation started")


@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    return JobStatusResponse(
        job_id=job.id, status=job.status.value, progress=job.progress,
        output_path=job.output_path, error=job.error, scenes_count=len(job.scenes)
    )


@app.get("/download/{job_id}")
async def download_video(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    if job.status.value != "completed":
        raise HTTPException(status_code=400, detail=f"Job not ready: {job.status.value}")
    return FileResponse(job.output_path, media_type="video/mp4", filename=f"{job_id}.mp4")


@app.get("/jobs")
async def list_jobs():
    """List all jobs with their status."""
    return [{"id": j.id, "status": j.status.value, "progress": j.progress} for j in jobs.values()]


@app.get("/health")
async def health():
    gpu = False
    try:
        import torch
        gpu = torch.cuda.is_available()
    except ImportError:
        pass
    return {"status": "ok", "gpu_available": gpu}


def _run_pipeline(job: Job):
    pipeline.run(job)
