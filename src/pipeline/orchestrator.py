"""Core pipeline orchestrator - manages the full video generation flow."""
import uuid
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    GENERATING_STORY = "generating_story"
    SCENE_SPLIT = "scene_split"
    GENERATING_IMAGES = "generating_images"
    GENERATING_AUDIO = "generating_audio"
    MIXING_MUSIC = "mixing_music"
    ANIMATING = "animating"
    COMPOSING_VIDEO = "composing_video"
    ADDING_SUBTITLES = "adding_subtitles"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: JobStatus = JobStatus.PENDING
    idea: str = ""
    story: str = ""
    style: str = "cartoon"
    content_type: str = "cartoon"
    scenes: list = field(default_factory=list)
    output_path: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    progress: float = 0.0
    subtitles: bool = True
    background_music: bool = True

    def to_dict(self):
        return asdict(self)


class Pipeline:
    """Sequential pipeline that orchestrates all modules."""

    def __init__(self, scene_gen, image_gen, tts_engine, animator, composer, storage,
                 story_gen=None, subtitle_gen=None, music_mixer=None):
        self.scene_gen = scene_gen
        self.image_gen = image_gen
        self.tts_engine = tts_engine
        self.animator = animator
        self.composer = composer
        self.storage = storage
        self.story_gen = story_gen
        self.subtitle_gen = subtitle_gen
        self.music_mixer = music_mixer

    def run(self, job: Job) -> Job:
        try:
            job.status = JobStatus.PROCESSING

            # Step 0: Generate story from idea
            if not job.story and job.idea:
                job.status = JobStatus.GENERATING_STORY
                if self.story_gen:
                    job.story = self.story_gen.generate(job.idea, job.content_type)
                else:
                    raise RuntimeError("No story text and no story generator configured")
            job.progress = 0.05

            # Step 1: Split story into scenes
            job.status = JobStatus.SCENE_SPLIT
            job.scenes = self.scene_gen.generate(job.story, job.style)
            job.progress = 0.1
            print(f"    Scenes: {len(job.scenes)}")

            total_scenes = len(job.scenes)

            for i, scene in enumerate(job.scenes):
                print(f"    Processing scene {i+1}/{total_scenes}...")

                # Step 2: Generate image
                job.status = JobStatus.GENERATING_IMAGES
                scene["image_path"] = self.image_gen.generate(
                    prompt=scene["image_prompt"],
                    style=job.style,
                    seed=scene.get("seed"),
                    scene_index=i
                )
                job.progress = 0.1 + (0.35 * (i + 1) / total_scenes)

                # Step 3: Generate audio
                job.status = JobStatus.GENERATING_AUDIO
                scene["audio_path"] = self.tts_engine.synthesize(
                    text=scene["narration"],
                    emotion=scene.get("emotion", "neutral"),
                    scene_index=i
                )
                job.progress = 0.45 + (0.15 * (i + 1) / total_scenes)

                # Step 4: Mix background music (if available)
                if job.background_music and self.music_mixer:
                    job.status = JobStatus.MIXING_MUSIC
                    music_file = self.music_mixer.pick_by_emotion(scene.get("emotion", "neutral"))
                    if music_file:
                        scene["audio_path"] = self.music_mixer.mix(
                            audio_path=scene["audio_path"],
                            music_path=music_file,
                        )

                # Step 5: Apply animation
                job.status = JobStatus.ANIMATING
                scene["video_clip_path"] = self.animator.animate(
                    image_path=scene["image_path"],
                    audio_path=scene["audio_path"],
                    motion=scene.get("motion", "zoom_in"),
                    scene_index=i
                )
                job.progress = 0.6 + (0.2 * (i + 1) / total_scenes)

            # Step 6: Compose final video
            job.status = JobStatus.COMPOSING_VIDEO
            output_path = self.composer.compose(scenes=job.scenes, job_id=job.id)
            job.progress = 0.85

            # Step 7: Add subtitles
            if job.subtitles and self.subtitle_gen:
                job.status = JobStatus.ADDING_SUBTITLES
                from src.core.config import Config
                config = Config()
                srt_path = str(config.temp_dir / f"{job.id}_subs.srt")
                self.subtitle_gen.generate_srt(job.scenes, srt_path)
                subtitled_path = str(config.output_dir / f"{job.id}_subtitled.mp4")
                output_path = self.subtitle_gen.burn_subtitles(output_path, srt_path, subtitled_path)
            job.progress = 0.95

            # Step 8: Store and finalize
            job.output_path = self.storage.save(output_path, job.id)
            job.status = JobStatus.COMPLETED
            job.progress = 1.0

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            import traceback
            traceback.print_exc()

        return job
