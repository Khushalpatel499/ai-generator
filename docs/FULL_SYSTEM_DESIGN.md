# Complete System Design Document
# AI Cartoon Video Generator - Full Architecture Specification

---

## 1. SYSTEM ARCHITECTURE

### Design Choice: **Modular Monolith with Pipeline Pattern**

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            PIPELINE ORCHESTRATOR                                  │
│                   (Event-driven Sequential Processing)                            │
└──────┬───────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│    STORY     │──▶│    SCENE     │──▶│    IMAGE     │──▶│     TTS      │
│  GENERATOR   │   │  BREAKDOWN   │   │  GENERATOR   │   │   ENGINE     │
│              │   │              │   │              │   │              │
│ • Ollama LLM │   │ • Rule-based │   │ • SD/SDXL    │   │ • Piper      │
│ • Templates  │   │ • LLM-based  │   │ • Seed lock  │   │ • Coqui      │
│ • 5 types    │   │ • Emotion    │   │ • LoRA       │   │ • Emotion    │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
                                                                │
       ┌────────────────────────────────────────────────────────┘
       ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  ANIMATION   │──▶│   VIDEO      │──▶│  SUBTITLES   │──▶│   STORAGE    │
│   LAYER      │   │  COMPOSER    │   │  GENERATOR   │   │   MODULE     │
│              │   │              │   │              │   │              │
│ • Ken Burns  │   │ • FFmpeg     │   │ • SRT gen    │   │ • Local FS   │
│ • Zoom/Pan   │   │ • Crossfade  │   │ • Burn-in    │   │ • YouTube    │
│ • Motion FX  │   │ • 1080p MP4  │   │ • Styling    │   │ • Job track  │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│                         REST API LAYER (FastAPI)                                  │
│                                                                                  │
│  POST /generate          - Submit idea or story                                  │
│  GET  /status/{job_id}   - Check progress                                        │
│  GET  /download/{job_id} - Download MP4                                          │
│  GET  /jobs              - List all jobs                                          │
│  GET  /health            - System health                                         │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Why Modular Monolith (not Microservices)?

| Factor | Microservices | Modular Monolith ✅ |
|--------|--------------|---------------------|
| Budget | Need Docker/K8s | Single process, zero infra |
| GPU sharing | Network overhead | Direct memory access |
| Complexity | Service discovery, etc | Just import modules |
| Latency | HTTP between services | In-process function calls |
| Scalability | Yes, but costly | Can split later easily |

Each module has a strict abstract interface → can be extracted to microservice by adding HTTP wrapper later.

---

## 2. CORE MODULES

### Module 1: Story Generator
- **Input:** Brief idea/topic string + content type
- **Output:** Full 300-500 word story
- **Implementation:** Ollama local LLM (Mistral 7B) with content-type templates
- **Fallback:** Rule-based template expansion (no LLM needed)
- **Content Types:** cartoon, motivation, funny, horror, educational

### Module 2: Scene Breakdown
- **Input:** Full story text + visual style
- **Output:** List of scene objects (narration, image prompt, emotion, motion, seed)
- **Implementation:** Rule-based (paragraph splitting + emotion detection) OR Ollama LLM
- **Key features:** Consistent seed generation, emotion-to-motion mapping

### Module 3: Image Generation
- **Input:** Text prompt + style + seed
- **Output:** PNG image file path
- **Implementation:** Stable Diffusion XL via `diffusers` library
- **Character consistency:** Seed locking + prompt templates + style prefixes
- **Fallback:** Colored placeholder images (for testing without GPU)

### Module 4: TTS Engine
- **Input:** Narration text + emotion
- **Output:** WAV audio file path
- **Implementation:** Piper TTS (fast, CPU) or Coqui TTS (expressive)
- **Emotion control:** Speed/pitch modulation per emotion type

### Module 5: Animation Layer
- **Input:** Image path + audio path + motion type
- **Output:** MP4 video clip
- **Implementation:** FFmpeg zoompan filter with preset motion curves
- **Effects:** zoom_in, zoom_out, pan_left, pan_right, ken_burns

### Module 6: Video Composer
- **Input:** List of scene clips
- **Output:** Final composed MP4
- **Implementation:** FFmpeg xfade transitions + audio crossfade
- **Quality:** 1080p, 24fps, H.264, AAC audio

### Module 7: Subtitle Generator
- **Input:** Scene list with narrations + timings
- **Output:** SRT file → burned into video
- **Implementation:** Custom SRT generator + FFmpeg subtitle filter

### Module 8: Storage
- **Input:** Final video path + job ID
- **Output:** Permanent file path
- **Implementation:** Local filesystem with JSON job tracking
- **Extension:** YouTube upload via OAuth2

---

## 3. TECH STACK (100% FREE)

| Layer | Tool | Cost | Notes |
|-------|------|------|-------|
| Language | Python 3.10+ | Free | Core runtime |
| API Framework | FastAPI | Free | Async, production-ready |
| Image Gen | Stable Diffusion XL | Free | Via HuggingFace diffusers |
| TTS | Piper TTS | Free | ONNX, runs on CPU |
| TTS Alt | Coqui TTS | Free | More expressive |
| Animation | FFmpeg | Free | Industry standard |
| Video | FFmpeg | Free | H.264 encoding |
| LLM | Ollama + Mistral 7B | Free | 4GB RAM, runs locally |
| LLM Alt | Ollama + Llama 3 | Free | Better quality, 8GB RAM |
| Frontend | React + Vite | Free | Optional web UI |
| Storage | Local filesystem | Free | Upgradeable to MinIO |
| YouTube | Google API (OAuth) | Free | 10K quota/day |

---

## 4. IMAGE GENERATION - CHARACTER CONSISTENCY

### Strategy 1: Seed Locking (Implemented)
```python
# Same seed = same noise = similar features
seed = hash("character_name") % 2**32
generator = torch.Generator().manual_seed(seed)
```
- Works for maintaining general style/composition
- Limitation: not pixel-perfect across different prompts

### Strategy 2: Prompt Templates (Implemented)
```python
CHARACTER_DB = {
    "hero": "a young boy with spiky blue hair, red cape, green eyes",
    "villain": "a tall dark figure with glowing purple eyes, black cloak"
}
# Prepend character description to EVERY scene prompt
prompt = f"{CHARACTER_DB['hero']}, {scene_specific_prompt}, {style}"
```

### Strategy 3: IP-Adapter (Free, no training)
```python
# Use a reference image to maintain face/style consistency
pipe.load_ip_adapter("h94/IP-Adapter", weight_name="ip-adapter_sdxl.bin")
pipe.set_ip_adapter_scale(0.6)  # Balance reference vs prompt
result = pipe(prompt=prompt, ip_adapter_image=reference_img)
```

### Strategy 4: LoRA Fine-tuning (Free, needs 10-20 images)
```bash
# Train custom character LoRA in ~30 min on Colab
accelerate launch train_dreambooth_lora_sdxl.py \
  --instance_prompt="sks_character" \
  --instance_data_dir="./my_character_images/" \
  --max_train_steps=500 \
  --output_dir="./models/lora/my_char"
```

### Strategy 5: Textual Inversion
```bash
# Learn a new embedding token for your character
accelerate launch textual_inversion.py \
  --learnable_property="object" \
  --placeholder_token="<my-hero>" \
  --initializer_token="boy"
```

### Style Support
- `cartoon` → "Disney-Pixar inspired, vibrant colors, clean lines"
- `anime` → "Studio Ghibli, soft watercolors, detailed backgrounds"
- `pixar` → "3D ray-traced, subsurface scattering, cinematic"
- `comic` → "Bold outlines, halftone dots, dynamic composition"

---

## 5. AUDIO SYSTEM

### TTS Architecture
```
Text → Emotion Detection → Speed/Pitch Adjustment → Piper/Coqui → WAV
```

### Emotion Control
| Emotion | Speed | Pitch Effect | Use Case |
|---------|-------|--------------|----------|
| happy | 1.1x | Slightly higher | Cartoon, funny |
| sad | 0.85x | Lower | Drama, motivation |
| angry | 1.2x | Intense | Action scenes |
| scared | 1.15x | Trembling | Horror |
| peaceful | 0.9x | Soft | Endings, nature |
| motivational | 0.95x | Strong, steady | Motivation videos |

### Scene-Based Audio Splitting
- Each scene generates its own WAV file independently
- Duration determines animation length (audio drives video timing)
- Silent padding between scenes handled by video composer

### Multi-Voice Support (Phase 2)
```python
# Piper supports multiple voices/models
VOICE_MAP = {
    "narrator": "en_US-lessac-medium",
    "child": "en_US-amy-medium",
    "villain": "en_GB-alan-medium",
}
```

---

## 6. VIDEO GENERATION SYSTEM

### Scene-Based Pipeline
```
For each scene:
  Image (1024x576) → zoompan filter → clip (duration = audio length) → scene_clip.mp4
All clips → xfade transitions → final.mp4
Optional: burn SRT subtitles → final_subtitled.mp4
```

### Transitions
- **Fade:** Default between all scenes (0.5s crossfade)
- **Zoom In:** For exciting/happy moments
- **Zoom Out:** For reflective/sad moments
- **Pan:** For establishing shots, environment
- **Ken Burns:** Slow combined zoom+pan for dramatic effect

### Audio-Video Sync
- TTS audio duration drives scene length (audio is master clock)
- FFmpeg `-shortest` flag ensures exact sync
- Crossfade transitions maintain audio continuity

### Output Specs
- Resolution: 1920x1080 (1080p) or 1280x720 (720p for CPU)
- FPS: 24 (cinematic)
- Codec: H.264 (libx264)
- Audio: AAC 192kbps
- Container: MP4

---

## 7. API DESIGN

### Input API
```
POST /generate
Body: {
    "story": "Full story text...",    // Option A: provide story
    "idea": "a robot learns to fly",  // Option B: AI generates story
    "style": "cartoon",               // cartoon|anime|pixar|comic
    "content_type": "motivation",     // cartoon|motivation|funny|horror|educational
    "subtitles": true
}
Response: { "job_id": "abc123", "status": "pending", "message": "Started" }
```

### Processing API
```
GET /status/{job_id}
Response: {
    "job_id": "abc123",
    "status": "generating_images",  // Real-time status
    "progress": 0.45,               // 0.0 to 1.0
    "scenes_count": 5,
    "error": null
}
```

### Output API
```
GET /download/{job_id}
Response: video/mp4 file stream

GET /jobs
Response: [{"id": "abc123", "status": "completed", "progress": 1.0}, ...]
```

---

## 8. COMPLETE DATA FLOW

```
┌────────────────────────────────────────────────────────────────────────┐
│                         FULL PIPELINE FLOW                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  INPUT                                                                 │
│    │                                                                   │
│    ├─ Option A: "idea" → StoryGenerator (Ollama) → full story text     │
│    │                                                                   │
│    └─ Option B: "story" → direct full story text                       │
│                                                                        │
│  STEP 1: SCENE BREAKDOWN                                               │
│    story_text → SceneGenerator → [scene_0, scene_1, ..., scene_n]      │
│    Each scene = {narration, image_prompt, emotion, motion, seed}        │
│                                                                        │
│  STEP 2: IMAGE GENERATION (per scene, parallelizable on multi-GPU)     │
│    scene.image_prompt → StableDiffusion(seed) → scene_000.png          │
│                                                                        │
│  STEP 3: TTS GENERATION (per scene, CPU-parallel)                      │
│    scene.narration + emotion → Piper/Coqui → audio_000.wav             │
│                                                                        │
│  STEP 4: ANIMATION (per scene)                                         │
│    scene_000.png + audio_000.wav → FFmpeg zoompan → clip_000.mp4       │
│                                                                        │
│  STEP 5: VIDEO COMPOSITION                                             │
│    [clip_000, clip_001, ...] → FFmpeg xfade → composed.mp4             │
│                                                                        │
│  STEP 6: SUBTITLES (optional)                                          │
│    scenes → SRT file → FFmpeg burn → final_subtitled.mp4               │
│                                                                        │
│  STEP 7: STORAGE + DELIVERY                                            │
│    final.mp4 → LocalStorage → download ready                           │
│    Optional: → YouTube upload via OAuth                                 │
│                                                                        │
│  OUTPUT: 1080p MP4 with narration + animation + subtitles              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 9. PRODUCTION FOLDER STRUCTURE

```
ai-video-generator/
├── src/
│   ├── __init__.py
│   ├── cli.py                        # Command-line interface
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py                   # FastAPI app + endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── interfaces.py             # Abstract base classes (contracts)
│   │   └── config.py                 # All configuration
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── story/
│   │   │   ├── __init__.py
│   │   │   ├── generator.py          # LLM story generation
│   │   │   └── input.py              # Story validation
│   │   ├── scene/
│   │   │   ├── __init__.py
│   │   │   └── generator.py          # Scene splitting (rule + LLM)
│   │   ├── image/
│   │   │   ├── __init__.py
│   │   │   └── generator.py          # SD + Dummy generators
│   │   ├── tts/
│   │   │   ├── __init__.py
│   │   │   └── engine.py             # Piper + Coqui + Dummy
│   │   ├── animation/
│   │   │   ├── __init__.py
│   │   │   └── animator.py           # FFmpeg motion effects
│   │   ├── video/
│   │   │   ├── __init__.py
│   │   │   ├── composer.py           # FFmpeg composition
│   │   │   └── subtitles.py          # SRT + burn-in
│   │   └── storage/
│   │       ├── __init__.py
│   │       ├── local.py              # Local filesystem storage
│   │       └── youtube.py            # YouTube upload automation
│   └── pipeline/
│       ├── __init__.py
│       └── orchestrator.py           # Job management + pipeline
├── config/
│   ├── default.toml                  # Default settings
│   └── client_secrets.json           # YouTube OAuth (user provides)
├── models/                           # Downloaded AI models
│   ├── en_US-lessac-medium.onnx      # Piper TTS model
│   └── lora/                         # Custom LoRA weights
├── output/                           # Generated videos
│   ├── temp/                         # Working files
│   └── jobs.json                     # Job tracking
├── assets/
│   ├── fonts/                        # Subtitle fonts
│   └── music/                        # Background music (royalty-free)
├── tests/
│   ├── test_scene_gen.py
│   ├── test_pipeline.py
│   └── test_api.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   └── example_scene_format.json
├── colab_notebook.py                 # Google Colab runner
├── requirements.txt                  # CPU dependencies
├── requirements-gpu.txt              # GPU dependencies
└── README.md
```

---

## 10. ENGINEERING PRINCIPLES

### Loose Coupling
- Every module implements an abstract base class from `interfaces.py`
- Pipeline only knows interfaces, never concrete implementations
- Config is injected, never hardcoded

### Replaceable Modules
```python
# Swap image generator without touching anything else:
pipeline = Pipeline(
    image_gen=StableDiffusionGenerator(config),  # ← swap this
    # image_gen=DummyImageGenerator(config),     # ← to this
    # image_gen=FluxGenerator(config),           # ← or a future one
    ...
)
```

### Error Handling & Fallback
```
LLM scene splitting fails → falls back to rule-based
SD image generation fails → falls back to placeholder
Piper TTS not installed  → falls back to silent audio
Crossfade too complex    → falls back to simple concat
YouTube upload fails     → video still saved locally
```

### Future SaaS Path
1. Replace in-memory jobs dict → Redis
2. Extract pipeline workers → separate processes
3. Replace LocalStorage → MinIO (S3-compatible)
4. Add auth layer → Supabase (free tier)
5. Add frontend → React + Vite on Vercel (free)

---

## 11. PERFORMANCE CONSTRAINTS

### Bottleneck Analysis

| Operation | CPU Time | GPU Time | Memory |
|-----------|----------|----------|--------|
| Story gen (LLM) | 10-30s | N/A | 4GB |
| Scene split (LLM) | 10-20s | N/A | 4GB |
| Image gen (SDXL) | 5-10 min/img | 20-40s/img | 6-8GB VRAM |
| Image gen (SD 1.5) | 2-5 min/img | 5-15s/img | 3-4GB VRAM |
| TTS (Piper) | 2-5s/scene | N/A | 500MB |
| Animation | 5-10s/scene | N/A | Low |
| Composition | 10-30s | N/A | Low |

### Hardware Strategies

**Low-end laptop (8GB RAM, no GPU):**
- Use SD 1.5 (not SDXL) - fits in CPU RAM
- Reduce to 512x288, upscale later
- Use 15 inference steps
- Sequential processing only
- Or: use DummyImageGenerator for testing pipeline

**Mid laptop (16GB RAM, no GPU):**
- SDXL with CPU offloading + attention slicing
- 768x432 resolution, upscale to 1080p via FFmpeg
- 20 inference steps

**Google Colab (free, T4 GPU):**
- Full SDXL, 1024x576, FP16
- 25-30 steps, xformers enabled
- Can process 5-scene video in ~10 minutes
- 12-hour runtime limit

**Colab Pro Alternative: Kaggle (also free):**
- P100 GPU, 30 hours/week
- Same setup as Colab

---

## 12. BONUS FEATURES

### Wav2Lip (Lip Sync)
```bash
# Generate a character face image → animate lips to match audio
git clone https://github.com/Rudrabha/Wav2Lip
python Wav2Lip/inference.py \
  --checkpoint_path wav2lip_gan.pth \
  --face character_face.png \
  --audio scene_audio.wav \
  --outfile lip_synced_clip.mp4
```

### AnimateDiff (Character Motion)
```python
# Instead of static images, generate 16-frame animations
from diffusers import AnimateDiffPipeline, MotionAdapter
adapter = MotionAdapter.from_pretrained("guoyww/animatediff-motion-adapter-v1-5-3")
pipe = AnimateDiffPipeline.from_pretrained("runwayml/stable-diffusion-v1-5", motion_adapter=adapter)
frames = pipe(prompt=scene_prompt, num_frames=16).frames[0]
```

### Multi-Language Support
```python
# Piper TTS has 30+ language models:
LANGUAGES = {
    "en": "en_US-lessac-medium",
    "de": "de_DE-thorsten-medium",
    "fr": "fr_FR-siwis-medium",
    "es": "es_ES-davefx-medium",
    "ja": "ja_JP-tohoku-medium",
    "hi": "hi_IN-madhu-medium",
}
# Just swap the model file - same interface!
```

### YouTube Automation Pipeline
```
Video Complete → Generate title/description (LLM) → Upload via OAuth → Schedule publish
```
- Free: 10,000 API units/day (enough for ~6 uploads)
- Auto-generates SEO-optimized title + description + tags via Ollama
- Can schedule posts for optimal engagement times

---

## QUICK START COMMANDS

```bash
# 1. Test pipeline (no GPU, no LLM, no TTS - just structure validation)
python -m src.cli --story "A brave little robot lived in a junkyard. Every night he looked at the stars and dreamed of flying. One day he found broken rocket parts and built his own ship. He launched into space trailing rainbow sparks." --style cartoon

# 2. With real TTS (download Piper model first)
python -m src.cli --story story.txt --tts piper --style anime

# 3. With LLM story generation (requires Ollama running)
python -m src.cli --idea "a cat who becomes a pirate" --type funny --use-llm

# 4. Full production (Colab with GPU)
python -m src.cli --idea "never give up on your dreams" --type motivation --style pixar --use-gpu --use-llm --tts piper

# 5. API server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# 6. API call
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"idea": "a dog who learns to fly", "content_type": "cartoon", "style": "anime"}'
```
