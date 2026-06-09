"""Image Generator - Stable Diffusion with character consistency strategies."""
from pathlib import Path
from typing import Optional
from src.core.interfaces import BaseImageGenerator
from src.core.config import Config


class StableDiffusionGenerator(BaseImageGenerator):
    """Generates images using Stable Diffusion with consistency techniques."""

    def __init__(self, config: Config):
        self.config = config
        self.pipe = None
        self._load_model()

    def _load_model(self):
        import torch
        from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

        device = self._get_device()
        dtype = torch.float16 if (device != "cpu" and self.config.use_fp16) else torch.float32

        self.pipe = StableDiffusionXLPipeline.from_pretrained(
            self.config.sd_model,
            torch_dtype=dtype,
            use_safetensors=True,
        )

        # Memory optimizations
        if self.config.enable_attention_slicing:
            self.pipe.enable_attention_slicing()

        if device == "cpu":
            self.pipe.enable_sequential_cpu_offload()
        else:
            self.pipe = self.pipe.to(device)

        # Faster scheduler
        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipe.scheduler.config
        )

    def _get_device(self) -> str:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def generate(self, prompt: str, style: str, seed: Optional[int] = None, scene_index: int = 0) -> str:
        import torch

        # Apply style prefix from config
        style_prefix = self.config.style_presets.get(style, "")
        full_prompt = f"{style_prefix}, {prompt}"

        negative_prompt = (
            "blurry, bad anatomy, bad hands, text, watermark, "
            "low quality, deformed, disfigured, ugly, duplicate"
        )

        # Seed locking for character consistency
        generator = torch.Generator(device="cpu")
        if seed is not None:
            generator.manual_seed(seed)

        image = self.pipe(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=self.config.sd_steps,
            guidance_scale=self.config.sd_guidance_scale,
            width=self.config.sd_width,
            height=self.config.sd_height,
            generator=generator,
        ).images[0]

        # Save image
        output_path = self.config.temp_dir / f"scene_{scene_index:03d}.png"
        image.save(output_path)
        return str(output_path)


class DummyImageGenerator(BaseImageGenerator):
    """Placeholder for testing without GPU - generates colored rectangles."""

    def __init__(self, config: Config):
        self.config = config

    def generate(self, prompt: str, style: str, seed: Optional[int] = None, scene_index: int = 0) -> str:
        from PIL import Image, ImageDraw, ImageFont
        import random

        if seed:
            random.seed(seed)

        # Create a colored placeholder image
        colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255),
                  (255, 255, 100), (255, 100, 255), (100, 255, 255)]
        color = colors[scene_index % len(colors)]

        img = Image.new('RGB', (self.config.sd_width, self.config.sd_height), color)
        draw = ImageDraw.Draw(img)

        # Add scene text
        text = f"Scene {scene_index + 1}\n{prompt[:80]}..."
        draw.text((50, 50), text, fill=(0, 0, 0))

        output_path = self.config.temp_dir / f"scene_{scene_index:03d}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        return str(output_path)
