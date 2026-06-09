"""TTS Engine - Neural text-to-speech with emotion control."""
import subprocess
import wave
from pathlib import Path
from typing import Optional
from src.core.interfaces import BaseTTSEngine
from src.core.config import Config


class PiperTTSEngine(BaseTTSEngine):
    """Uses Piper TTS (fast, runs on CPU, high quality)."""

    def __init__(self, config: Config):
        self.config = config
        self.model = config.piper_model
        self.speed = config.piper_speed

    def synthesize(self, text: str, emotion: str = "neutral", scene_index: int = 0) -> str:
        output_path = self.config.temp_dir / f"audio_{scene_index:03d}.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Piper speed adjustment based on emotion
        speed = self._emotion_to_speed(emotion)

        # Piper expects text via stdin, outputs wav
        cmd = [
            "piper",
            "--model", str(self.config.models_dir / f"{self.model}.onnx"),
            "--output_file", str(output_path),
            "--length_scale", str(1.0 / speed),
        ]

        proc = subprocess.run(
            cmd,
            input=text.encode(),
            capture_output=True,
            timeout=60
        )

        if proc.returncode != 0:
            raise RuntimeError(f"Piper TTS failed: {proc.stderr.decode()}")

        return str(output_path)

    def _emotion_to_speed(self, emotion: str) -> float:
        speeds = {
            "happy": 1.1,
            "sad": 0.85,
            "angry": 1.2,
            "scared": 1.15,
            "peaceful": 0.9,
            "neutral": 1.0,
        }
        return speeds.get(emotion, 1.0) * self.speed


class CoquiTTSEngine(BaseTTSEngine):
    """Uses Coqui TTS (more expressive, needs more resources)."""

    def __init__(self, config: Config):
        self.config = config
        self.tts = None

    def _load_model(self):
        if self.tts is None:
            from TTS.api import TTS
            self.tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")

    def synthesize(self, text: str, emotion: str = "neutral", scene_index: int = 0) -> str:
        self._load_model()
        output_path = self.config.temp_dir / f"audio_{scene_index:03d}.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.tts.tts_to_file(
            text=text,
            file_path=str(output_path),
            speed=self._emotion_to_speed(emotion)
        )
        return str(output_path)

    def _emotion_to_speed(self, emotion: str) -> float:
        speeds = {"happy": 1.1, "sad": 0.85, "angry": 1.2, "neutral": 1.0}
        return speeds.get(emotion, 1.0)


class DummyTTSEngine(BaseTTSEngine):
    """Generates silent audio for testing."""

    def __init__(self, config: Config):
        self.config = config

    def synthesize(self, text: str, emotion: str = "neutral", scene_index: int = 0) -> str:
        output_path = self.config.temp_dir / f"audio_{scene_index:03d}.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate silent WAV based on text length (~150 words/min speaking rate)
        word_count = len(text.split())
        duration_sec = max(2.0, word_count / 2.5)  # ~150 wpm
        sample_rate = 22050
        n_frames = int(duration_sec * sample_rate)

        with wave.open(str(output_path), 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b'\x00\x00' * n_frames)

        return str(output_path)
