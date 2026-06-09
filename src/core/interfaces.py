"""Abstract base classes for all modules - enforces loose coupling."""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseSceneGenerator(ABC):
    """Splits a story into structured scenes."""

    @abstractmethod
    def generate(self, story: str, style: str) -> List[Dict]:
        """Returns list of scene dicts with: narration, image_prompt, emotion, motion, duration."""
        ...


class BaseImageGenerator(ABC):
    """Generates images from text prompts."""

    @abstractmethod
    def generate(self, prompt: str, style: str, seed: Optional[int] = None, scene_index: int = 0) -> str:
        """Returns path to generated image."""
        ...


class BaseTTSEngine(ABC):
    """Converts text to speech audio."""

    @abstractmethod
    def synthesize(self, text: str, emotion: str = "neutral", scene_index: int = 0) -> str:
        """Returns path to generated audio file."""
        ...


class BaseAnimator(ABC):
    """Applies motion effects to static images."""

    @abstractmethod
    def animate(self, image_path: str, audio_path: str, motion: str = "zoom_in", scene_index: int = 0) -> str:
        """Returns path to animated video clip."""
        ...


class BaseComposer(ABC):
    """Composes final video from scene clips."""

    @abstractmethod
    def compose(self, scenes: List[Dict], job_id: str) -> str:
        """Returns path to final composed video."""
        ...


class BaseStorage(ABC):
    """Handles file storage and retrieval."""

    @abstractmethod
    def save(self, file_path: str, job_id: str) -> str:
        """Moves/copies file to permanent storage. Returns final path."""
        ...

    @abstractmethod
    def get_path(self, job_id: str) -> Optional[str]:
        """Returns the output path for a job."""
        ...
