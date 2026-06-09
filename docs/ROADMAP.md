# Implementation Roadmap & Full Design Specification

## Phase 1: MVP (Week 1-2) - What's Built Now

**Goal:** Story text → video with placeholder images + silent audio + Ken Burns animation

### What works immediately:
1. ✅ Rule-based scene splitting (no LLM needed)
2. ✅ Dummy image generator (colored placeholders)
3. ✅ Dummy TTS (silent audio, correct duration)
4. ✅ FFmpeg animation (zoom, pan, Ken Burns)
5. ✅ FFmpeg video composition (crossfade transitions)
6. ✅ CLI interface
7. ✅ REST API (FastAPI)
8. ✅ Local storage with job tracking

### To activate REAL image generation:
```bash
pip install diffusers transformers accelerate torch
# Then use --use-gpu flag or switch DummyImageGenerator → StableDiffusionGenerator
```

### To activate REAL TTS:
```bash
pip install piper-tts
wget -O models/en_US-lessac-medium.onnx [piper-voices-url]
# Then use --tts piper flag
```

---

## Phase 2: Quality Improvements (Week 3-5)

### 2.1 LLM Scene Intelligence
```bash
# Install Ollama (free local LLM)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull mistral

# Use --use-llm flag
python -m src.cli --story story.txt --use-llm
```

Benefits: Better scene splitting, more descriptive image prompts, emotion detection.

### 2.2 Character Consistency

**Strategy 1: Prompt Engineering (Free, No Training)**
```python
CHARACTER_TEMPLATE = {
    "ruby": "a small red fox with bright green eyes and a white-tipped tail",
    "mordecai": "a large menacing black raven with glowing red eyes"
}

# Prepend to every scene prompt
full_prompt = f"{CHARACTER_TEMPLATE['ruby']}, {scene_prompt}, {style}"
```

**Strategy 2: Seed Locking (Already implemented)**
- Same seed = same noise pattern = similar character features
- Works best with consistent prompt structure

**Strategy 3: IP-Adapter (Free, no training needed)**
```python
from diffusers import StableDiffusionXLPipeline
from diffusers.utils import load_image

# Use a reference image to maintain consistency
pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.bin")
pipe.set_ip_adapter_scale(0.6)
image = pipe(prompt=scene_prompt, ip_adapter_image=reference_image).images[0]
```

**Strategy 4: LoRA Fine-tuning (Free, needs 10-20 images)**
```bash
# Train a LoRA on your character
accelerate launch train_dreambooth_lora_sdxl.py \
  --pretrained_model_name_or_path="stabilityai/stable-diffusion-xl-base-1.0" \
  --instance_data_dir="./training_images/ruby/" \
  --instance_prompt="a photo of sks ruby fox" \
  --output_dir="./models/lora/ruby" \
  --resolution=1024 \
  --train_batch_size=1 \
  --max_train_steps=500
```

### 2.3 Background Music
```python
# Add royalty-free music from assets/music/
# Mix at low volume behind TTS audio
ffmpeg -i scene_audio.wav -i background_music.mp3 \
  -filter_complex "[1:a]volume=0.15[bg];[0:a][bg]amix=inputs=2:duration=first" \
  output_with_music.wav
```

### 2.4 Subtitles
```python
# Generate SRT from scene narrations
# Burn into video with FFmpeg
ffmpeg -i video.mp4 -vf subtitles=subs.srt output_with_subs.mp4
```

---

## Phase 3: SaaS Architecture (Week 6+)

### Infrastructure (All Free Tier)

| Component | Free Option |
|-----------|-------------|
| Compute | Google Colab / Kaggle Free GPU |
| Queue | Redis (self-hosted) or BullMQ |
| Storage | MinIO (S3-compatible, self-hosted) |
| Database | SQLite → PostgreSQL |
| Frontend | React + Vite (Vercel free tier) |
| Auth | Supabase free tier |
| Monitoring | Grafana + Prometheus (self-hosted) |

### Architecture Changes

```python
# 1. Replace in-memory job store with Redis
import redis
r = redis.Redis()
r.set(f"job:{job_id}", json.dumps(job.to_dict()))

# 2. Worker process (separate from API)
while True:
    job_data = r.brpop("video_queue")
    job = Job(**json.loads(job_data))
    pipeline.run(job)
    r.set(f"job:{job.id}", json.dumps(job.to_dict()))

# 3. API just enqueues jobs
@app.post("/generate")
async def generate(req: GenerateRequest):
    job = Job(story=req.story)
    r.lpush("video_queue", json.dumps(job.to_dict()))
    return {"job_id": job.id}
```

### YouTube Automation Pipeline

```python
# Uses youtube-upload (free, uses OAuth)
# pip install google-api-python-client google-auth-oauthlib

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_to_youtube(video_path, title, description):
    youtube = build('youtube', 'v3', credentials=creds)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description, "categoryId": "24"},
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(video_path, mimetype='video/mp4')
    )
    return request.execute()
```

---

## Bonus Features

### Wav2Lip (Lip Sync)
```bash
git clone https://github.com/Rudrabha/Wav2Lip.git
# Generate a face image → animate lips to match audio
python inference.py --checkpoint_path wav2lip_gan.pth \
  --face face.png --audio scene_audio.wav --outfile lip_synced.mp4
```

### AnimateDiff (Character Motion)
```python
from diffusers import AnimateDiffPipeline, MotionAdapter
adapter = MotionAdapter.from_pretrained("guoyww/animatediff-motion-adapter-v1-5-3")
pipe = AnimateDiffPipeline.from_pretrained("runwayml/stable-diffusion-v1-5", motion_adapter=adapter)
# Generates short animated clips instead of static images
```

### Multilingual TTS
```python
# Piper supports 30+ languages
# Just download the appropriate model:
# models/de_DE-thorsten-medium.onnx  (German)
# models/fr_FR-siwis-medium.onnx    (French)
# models/es_ES-davefx-medium.onnx   (Spanish)
# models/ja_JP-tohoku-medium.onnx   (Japanese)
```

---

## API Design Between Modules

### Internal Module Communication (Pipeline Pattern)

```
Pipeline.run(job) calls each module sequentially:

SceneGenerator.generate(story, style) → List[SceneDict]
ImageGenerator.generate(prompt, style, seed, index) → str (image_path)
TTSEngine.synthesize(text, emotion, index) → str (audio_path)
Animator.animate(image_path, audio_path, motion, index) → str (clip_path)
Composer.compose(scenes, job_id) → str (video_path)
Storage.save(file_path, job_id) → str (final_path)
```

### External REST API

```
POST /generate
  Body: { "story": str, "style": str }
  Response: { "job_id": str, "status": str }

GET /status/{job_id}
  Response: { "job_id": str, "status": str, "progress": float, "output_path": str? }

GET /download/{job_id}
  Response: video/mp4 file stream

GET /health
  Response: { "status": "ok", "gpu_available": bool }
```

---

## Memory & Performance Management

### 8GB RAM Strategy
- Load SD model with attention slicing + sequential CPU offload
- Process one scene at a time (no parallelism)
- Unload SD model before video composition
- Use SD 1.5 instead of SDXL (2GB vs 6GB VRAM)

### 16GB RAM Strategy
- SDXL with FP16 (fits in ~6GB VRAM)
- Can keep model loaded across scenes
- Parallel TTS generation (CPU) while image gen (GPU)

### Colab Strategy (15GB GPU RAM)
- Full SDXL with xformers
- Higher inference steps (30-50)
- Batch processing multiple scenes
- Runtime limit: ~12 hours, save checkpoints
