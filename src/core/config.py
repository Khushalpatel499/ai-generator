"""Configuration management - all settings in one place."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Paths
    base_dir: Path = Path(".")
    output_dir: Path = Path("./output")
    models_dir: Path = Path("./models")
    temp_dir: Path = Path("./output/temp")

    # Image Generation
    sd_model: str = "stabilityai/stable-diffusion-xl-base-1.0"  # or use smaller: "runwayml/stable-diffusion-v1-5"
    sd_steps: int = 20  # Reduce for speed on CPU
    sd_guidance_scale: float = 7.5
    sd_width: int = 1024
    sd_height: int = 576  # 16:9 for YouTube
    use_fp16: bool = True
    enable_attention_slicing: bool = True

    # TTS
    tts_engine: str = "piper"  # "piper" or "coqui"
    piper_model: str = "en_US-lessac-medium"
    piper_speed: float = 1.0

    # Video
    video_fps: int = 24
    video_resolution: tuple = (1920, 1080)
    transition_duration: float = 0.5
    output_format: str = "mp4"

    # Scene Generation
    scene_generator: str = "rule_based"  # "rule_based" or "llm"
    llm_model: str = "mistral"  # For Ollama local LLM

    # Style presets
    style_presets: dict = field(default_factory=lambda: {
        "cartoon": "cartoon style, vibrant colors, clean lines, Disney-Pixar inspired, detailed background, cinematic lighting",
        "anime": "anime style, Studio Ghibli inspired, soft colors, detailed, 4k, beautiful scenery",
        "pixar": "3D Pixar style, ray tracing, subsurface scattering, hyperdetailed, cinematic",
        "comic": "comic book style, bold outlines, halftone dots, vibrant pop colors, dynamic composition",
    })

    # Animation presets
    motion_presets: dict = field(default_factory=lambda: {
        "zoom_in": {"scale_start": 1.0, "scale_end": 1.2},
        "zoom_out": {"scale_start": 1.2, "scale_end": 1.0},
        "pan_left": {"x_start": 0, "x_end": -100},
        "pan_right": {"x_start": 0, "x_end": 100},
        "ken_burns": {"scale_start": 1.0, "scale_end": 1.15, "x_start": 0, "x_end": 50},
    })

    def ensure_dirs(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
