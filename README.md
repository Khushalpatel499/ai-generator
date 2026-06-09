# AI Cartoon Video Generator 🎬

**Zero-budget, open-source AI system that converts text stories into cartoon-style videos.**

> Text Story → Scenes → Images → Voiceover → Animation → Final MP4

## Quick Start

### Prerequisites
- Python 3.10+
- FFmpeg installed and in PATH
- 8GB+ RAM (16GB recommended)
- GPU optional but recommended for image generation

### Installation

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/ai-video-generator.git
cd ai-video-generator

# Install (CPU-only, for testing)
pip install -r requirements.txt

# Install (GPU, for production quality)
pip install -r requirements-gpu.txt

# Download Piper TTS model
mkdir -p models
wget -O models/en_US-lessac-medium.onnx https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
```

### Usage

#### CLI
```bash
# Quick test (dummy images + silent audio)
python -m src.cli --story "A brave knight found a dragon..." --style cartoon

# With GPU (real Stable Diffusion images)
python -m src.cli --story story.txt --style anime --use-gpu

# With local LLM scene splitting (requires Ollama)
python -m src.cli --story story.txt --use-llm --use-gpu --tts piper
```

#### API Server
```bash
uvicorn src.api.main:app --reload --port 8000

# Generate video
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"story": "A brave knight...", "style": "cartoon"}'

# Check status
curl http://localhost:8000/status/{job_id}

# Download
curl -O http://localhost:8000/download/{job_id}
```

#### Google Colab (Free GPU)
Open `colab_notebook.py` in Google Colab for free GPU access.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full system design.

```
Story → SceneGenerator → ImageGenerator → TTSEngine → Animator → Composer → MP4
```

Each module implements an abstract interface and can be swapped independently.

## Styles Available
- `cartoon` - Disney/Pixar inspired
- `anime` - Studio Ghibli style
- `pixar` - 3D ray-traced look
- `comic` - Bold comic book style

## Tech Stack (All Free)

| Component | Tool | Notes |
|-----------|------|-------|
| Image Gen | Stable Diffusion XL | Via diffusers library |
| TTS | Piper / Coqui TTS | Neural, runs on CPU |
| Animation | FFmpeg | Ken Burns, zoom, pan |
| Video | FFmpeg | Crossfade transitions |
| LLM | Ollama (Mistral) | Local, optional |
| API | FastAPI | Async, production-ready |
| Scene Split | Rule-based / LLM | Configurable |

## Project Structure

```
ai-video-generator/
├── src/
│   ├── api/              # FastAPI REST endpoints
│   │   └── main.py
│   ├── core/             # Shared interfaces & config
│   │   ├── interfaces.py # Abstract base classes
│   │   └── config.py
│   ├── modules/          # Pluggable modules
│   │   ├── scene/        # Story → scenes
│   │   ├── image/        # Text → images (SD)
│   │   ├── tts/          # Text → speech
│   │   ├── animation/    # Image → animated clip
│   │   ├── video/        # Clips → final video
│   │   └── storage/      # Output management
│   ├── pipeline/         # Orchestration logic
│   │   └── orchestrator.py
│   └── cli.py            # Command-line interface
├── config/               # Configuration files
├── models/               # Downloaded AI models
├── output/               # Generated videos
├── assets/               # Fonts, music, etc.
├── tests/                # Unit & integration tests
├── docs/                 # Architecture docs
├── colab_notebook.py     # Google Colab runner
├── requirements.txt      # CPU dependencies
└── requirements-gpu.txt  # Full GPU dependencies
```

## Roadmap

### Phase 1: MVP ✅ (Current)
- [x] Pipeline architecture
- [x] Rule-based scene splitting
- [x] Image generation (SD / placeholder)
- [x] TTS integration (Piper/Coqui/Dummy)
- [x] FFmpeg animation (Ken Burns effects)
- [x] Video composition with transitions
- [x] CLI + REST API

### Phase 2: Quality
- [ ] Ollama LLM scene intelligence
- [ ] LoRA training for character consistency
- [ ] Background music integration
- [ ] Subtitle overlay
- [ ] Multiple voice support

### Phase 3: Scale → SaaS
- [ ] Redis job queue
- [ ] GPU worker pool
- [ ] MinIO storage (S3-compatible)
- [ ] User authentication
- [ ] React frontend
- [ ] YouTube auto-upload

### Bonus Features
- [ ] Wav2Lip lip sync
- [ ] Character motion (AnimateDiff)
- [ ] Multilingual TTS
- [ ] Batch processing

## Character Consistency Strategies

1. **Seed Locking** - Same seed per character across scenes
2. **Prompt Templates** - Consistent character descriptions appended to every prompt
3. **LoRA Fine-tuning** - Train a LoRA on your character (5-20 images needed)
4. **IP-Adapter** - Reference image conditioning (no training needed)
5. **Textual Inversion** - Learn embeddings for consistent characters

## Performance Tips

- Use `--sd-steps 15` for faster generation (slight quality loss)
- Enable `xformers` for 40% memory reduction
- Use FP16 on GPU (enabled by default)
- Reduce resolution to 768x432 for CPU testing
- Process scenes in parallel if you have multiple GPUs

## License

MIT - Use freely, modify freely, sell freely.
