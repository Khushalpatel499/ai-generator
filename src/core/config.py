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
    sd_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    sd_steps: int = 25
    sd_guidance_scale: float = 7.5
    sd_width: int = 1024
    sd_height: int = 576  # 16:9 for YouTube
    use_fp16: bool = True
    enable_attention_slicing: bool = True

    # Negative prompt (what to avoid in images)
    negative_prompt: str = (
        "blurry, bad anatomy, bad hands, text, watermark, signature, "
        "low quality, deformed, disfigured, ugly, duplicate, morbid, "
        "mutilated, extra limbs, extra fingers, poorly drawn hands, "
        "poorly drawn face, mutation, out of frame, cropped, worst quality, "
        "low res, jpeg artifacts, username, error"
    )

    # TTS
    tts_engine: str = "piper"
    piper_model: str = "en_US-lessac-medium"
    piper_speed: float = 1.0

    # Music
    music_enabled: bool = True
    music_volume: float = 0.12  # Subtle background

    # Video
    video_fps: int = 24
    video_resolution: tuple = (1920, 1080)
    transition_duration: float = 0.8  # Slightly longer transitions
    output_format: str = "mp4"

    # Scene Generation
    scene_generator: str = "enhanced"  # "rule_based", "enhanced", or "llm"
    llm_model: str = "mistral"

    # Style presets (improved with more detail)
    style_presets: dict = field(default_factory=lambda: {
        "cartoon": (
            "cartoon style, vibrant saturated colors, clean bold lines, "
            "Disney-Pixar inspired, detailed lush background, cinematic lighting, "
            "professional digital art, trending on artstation, 8k"
        ),
        "anime": (
            "anime style, Studio Ghibli inspired, soft watercolor colors, "
            "highly detailed, beautiful atmospheric scenery, cel shading, "
            "makoto shinkai style lighting, 4k, masterpiece"
        ),
        "pixar": (
            "3D Pixar style, ray tracing, subsurface scattering, "
            "hyperdetailed textures, cinematic depth of field, "
            "octane render, volumetric lighting, 8k resolution"
        ),
        "comic": (
            "comic book style, bold black outlines, halftone dots, "
            "vibrant pop art colors, dynamic composition, splash page, "
            "Marvel DC style, action pose, dramatic shadows"
        ),
        "realistic_cartoon": (
            "semi-realistic cartoon, detailed faces, expressive eyes, "
            "rich textures, cinematic color grading, studio quality, "
            "concept art style, artstation winner, 4k"
        ),
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
        (self.base_dir / "assets" / "music").mkdir(parents=True, exist_ok=True)
