# -*- coding: utf-8 -*-
"""AI_Cartoon_Video_Generator.ipynb

# AI Cartoon Video Generator - Google Colab (FREE GPU)
Generate real cartoon videos with AI - completely free!

## How to use:
1. Click "Runtime" > "Change runtime type" > Select "T4 GPU"
2. Run all cells in order
3. Your video will be downloadable at the end
"""

# ============================================================
# CELL 1: Install Dependencies (run once)
# ============================================================
# !pip install -q diffusers transformers accelerate torch safetensors
# !pip install -q Pillow requests pydantic fastapi
# !pip install -q piper-tts
# !apt-get install -qq ffmpeg > /dev/null 2>&1
# !pip install -q xformers

# # Clone your repo (CHANGE THIS URL to your GitHub repo)
# !git clone https://github.com/YOUR_USERNAME/ai-video-generator.git
# %cd ai-video-generator

# # Download Piper TTS model
# !mkdir -p models
# !wget -q -O models/en_US-lessac-medium.onnx https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
# !wget -q -O models/en_US-lessac-medium.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

print("Dependencies installed!")

# ============================================================
# CELL 2: Verify GPU
# ============================================================
import torch
print(f"GPU Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Name: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
else:
    print("WARNING: No GPU! Go to Runtime > Change runtime type > T4 GPU")

# ============================================================
# CELL 3: Generate Video (EDIT YOUR STORY/IDEA HERE)
# ============================================================
import sys
sys.path.insert(0, '.')

from src.core.config import Config
from src.pipeline.orchestrator import Pipeline, Job
from src.modules.scene.generator import RuleBasedSceneGenerator
from src.modules.image.generator import StableDiffusionGenerator
from src.modules.tts.engine import PiperTTSEngine
from src.modules.animation.animator import FFmpegAnimator
from src.modules.video.composer import FFmpegComposer
from src.modules.video.subtitles import SubtitleGenerator
from src.modules.storage.local import LocalStorage

# === CONFIGURATION ===
config = Config()
config.sd_model = "stabilityai/stable-diffusion-xl-base-1.0"  # Best quality
# config.sd_model = "runwayml/stable-diffusion-v1-5"  # Faster, less VRAM
config.sd_steps = 25
config.sd_width = 1024
config.sd_height = 576  # 16:9 for YouTube
config.use_fp16 = True
config.enable_attention_slicing = True
config.ensure_dirs()

# === BUILD PIPELINE ===
pipeline = Pipeline(
    scene_gen=RuleBasedSceneGenerator(),
    image_gen=StableDiffusionGenerator(config),
    tts_engine=PiperTTSEngine(config),
    animator=FFmpegAnimator(config),
    composer=FFmpegComposer(config),
    storage=LocalStorage(config),
    subtitle_gen=SubtitleGenerator(),
)

# === YOUR STORY (EDIT THIS!) ===
story = """
A brave little robot named Bolt lived in a junkyard at the edge of the city.
Every night, he would look up at the stars and dream of flying.

One day, he found a broken rocket ship buried under old car parts.
He spent weeks repairing it, using spare gears and colorful wires.

Finally, the day came. Bolt climbed into the rocket and pressed the big red button.
He soared into the sky, leaving a trail of rainbow sparks behind him.

He flew past the clouds, past the birds, all the way to the moon.
And there, standing on the silver surface, Bolt finally felt free.
"""

# === STYLE OPTIONS: "cartoon", "anime", "pixar", "comic" ===
style = "cartoon"

# === RUN! ===
job = Job(story=story, style=style, subtitles=True)
print(f"Starting generation [Job: {job.id}]")
print(f"Style: {style}")
print(f"Scenes will be generated with real Stable Diffusion images...")
print()

result = pipeline.run(job)

if result.status.value == "completed":
    print(f"\n[DONE] Video generated: {result.output_path}")
    print(f"       Scenes: {len(result.scenes)}")
    for i, s in enumerate(result.scenes):
        print(f"       Scene {i+1}: {s['emotion']} - {s['narration'][:50]}...")
else:
    print(f"\n[FAIL] {result.error}")

# ============================================================
# CELL 4: Play video in Colab
# ============================================================
from IPython.display import HTML
from base64 import b64encode

if result.status.value == "completed":
    video_path = result.output_path
    with open(video_path, "rb") as f:
        video_data = b64encode(f.read()).decode()
    
    display(HTML(f"""
    <video width="800" controls>
        <source src="data:video/mp4;base64,{video_data}" type="video/mp4">
    </video>
    """))

# ============================================================
# CELL 5: Download video
# ============================================================
from google.colab import files
if result.status.value == "completed":
    files.download(result.output_path)
    print("Download started!")
