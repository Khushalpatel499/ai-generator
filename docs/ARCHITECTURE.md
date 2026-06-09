# AI Cartoon Video Generator - System Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PIPELINE ORCHESTRATOR                                │
│                    (Event-driven Sequential Pipeline)                         │
└─────────┬───────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  STORY INPUT    │───▶│ SCENE GENERATOR │───▶│ IMAGE GENERATOR │
│                 │    │                 │    │                 │
│ - Raw text      │    │ - LLM splitting │    │ - Stable Diff   │
│ - File upload   │    │ - Prompt craft  │    │ - LoRA/style    │
│ - URL scrape    │    │ - Timing calc   │    │ - Seed locking  │
└─────────────────┘    └─────────────────┘    └────────┬────────┘
                                                        │
          ┌─────────────────────────────────────────────┘
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   TTS ENGINE    │───▶│ANIMATION LAYER  │───▶│ VIDEO COMPOSER  │
│                 │    │                 │    │                 │
│ - Piper TTS    │    │ - Ken Burns     │    │ - FFmpeg        │
│ - Coqui TTS    │    │ - Zoom/Pan      │    │ - MoviePy       │
│ - Emotion ctrl │    │ - Transitions   │    │ - Audio sync    │
└─────────────────┘    └─────────────────┘    └────────┬────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │    STORAGE       │
                                              │                 │
                                              │ - Local FS      │
                                              │ - Job tracking  │
                                              │ - MP4 output    │
                                              └─────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER (FastAPI)                              │
│         POST /generate  |  GET /status/{id}  |  GET /download/{id}           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Architecture Decision: Modular Monolith

**Why NOT microservices:**
- Zero budget = no Kubernetes, no Docker orchestration overhead
- Single laptop = no network latency benefit from splitting
- GPU sharing between services would be a nightmare

**Why Modular Monolith:**
- Each module has strict interface contracts (abstract base classes)
- Modules communicate through a pipeline bus (in-process events)
- Any module can be swapped without touching others
- Can be split into microservices later by just adding HTTP wrappers
- Single process = efficient GPU/memory sharing

## Data Flow

```
1. User submits story text via API or CLI
2. Pipeline Orchestrator creates a Job with unique ID
3. StoryModule validates and stores raw text
4. SceneGenerator splits story into scenes (via local LLM or rule-based)
5. For each scene:
   a. ImageGenerator creates cartoon image (Stable Diffusion)
   b. TTSEngine generates voiceover audio
   c. AnimationLayer applies motion effects to image
6. VideoComposer stitches all scenes with transitions + audio
7. Final MP4 saved to storage, job marked complete
```

## Key Design Patterns

- **Strategy Pattern**: Each module has a base interface, multiple implementations
- **Pipeline Pattern**: Linear flow with event hooks
- **Factory Pattern**: Model loading based on config
- **Observer Pattern**: Progress tracking and logging

## Performance Bottlenecks & Mitigation

| Bottleneck | Impact | Mitigation |
|---|---|---|
| Image Generation (SD) | 30-60s per image on CPU | GPU priority, batch on Colab, reduce steps |
| TTS Generation | 5-10s per scene | Lightweight Piper model, parallel on CPU |
| Video Encoding | 10-30s | FFmpeg hardware accel, preset tuning |
| Memory (SD model) | 4-8GB VRAM | FP16, attention slicing, CPU offload |

## GPU vs CPU Fallback Strategy

```python
# Automatic detection
if torch.cuda.is_available():
    device = "cuda"
    dtype = torch.float16
elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
    device = "mps"  # Apple Silicon
    dtype = torch.float16
else:
    device = "cpu"
    dtype = torch.float32
    # Enable: attention slicing, sequential CPU offload, reduced steps
```

## Scaling to SaaS (Phase 3)

```
                    ┌──────────────┐
                    │   NGINX LB   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ API Pod  │ │ API Pod  │ │ API Pod  │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                    ┌──────────────┐
                    │  Redis Queue │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │GPU Worker│ │GPU Worker│ │GPU Worker│
        └──────────┘ └──────────┘ └──────────┘
                           │
                    ┌──────┴───────┐
                    │  S3 / MinIO  │
                    └──────────────┘
```

- API layer becomes stateless
- Redis/RabbitMQ for job queuing
- GPU workers pull jobs independently
- MinIO (free S3-compatible) for storage
- PostgreSQL for job metadata
