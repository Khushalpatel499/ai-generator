"""Scene Generator - splits story into structured scenes using rule-based or LLM approach."""
import json
import re
import hashlib
from typing import List, Dict
from src.core.interfaces import BaseSceneGenerator


class RuleBasedSceneGenerator(BaseSceneGenerator):
    """Splits story by paragraphs/sentences with heuristic prompt generation."""

    EMOTION_KEYWORDS = {
        "happy": ["happy", "joy", "laugh", "smile", "celebrate", "excited"],
        "sad": ["sad", "cry", "tears", "lonely", "grief", "miss"],
        "angry": ["angry", "fury", "rage", "shout", "fight"],
        "scared": ["scared", "fear", "dark", "horror", "tremble"],
        "peaceful": ["calm", "peace", "quiet", "serene", "gentle"],
    }

    MOTION_MAP = {
        "happy": "zoom_in",
        "sad": "zoom_out",
        "angry": "ken_burns",
        "scared": "pan_left",
        "peaceful": "pan_right",
    }

    def generate(self, story: str, style: str) -> List[Dict]:
        paragraphs = [p.strip() for p in story.split("\n\n") if p.strip()]

        # If no double newlines, split by sentences (3-4 per scene)
        if len(paragraphs) <= 1:
            sentences = re.split(r'(?<=[.!?])\s+', story.strip())
            paragraphs = []
            for i in range(0, len(sentences), 3):
                paragraphs.append(" ".join(sentences[i:i+3]))

        scenes = []
        for i, para in enumerate(paragraphs):
            emotion = self._detect_emotion(para)
            seed = int(hashlib.md5(f"scene_{i}".encode()).hexdigest()[:8], 16) % 2**32

            scenes.append({
                "scene_index": i,
                "narration": para,
                "image_prompt": self._build_image_prompt(para, style),
                "emotion": emotion,
                "motion": self.MOTION_MAP.get(emotion, "zoom_in"),
                "seed": seed,
                "duration": None,  # Will be set by TTS audio length
            })

        return scenes

    def _detect_emotion(self, text: str) -> str:
        text_lower = text.lower()
        scores = {}
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            scores[emotion] = sum(1 for kw in keywords if kw in text_lower)
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "neutral"

    def _build_image_prompt(self, narration: str, style: str) -> str:
        # Extract key visual elements from narration
        # Remove dialogue, keep descriptions
        visual = re.sub(r'"[^"]*"', '', narration)
        visual = visual[:200]  # Trim for SD prompt length
        return f"{visual}, {style} style, high quality, detailed, 4k"


class OllamaSceneGenerator(BaseSceneGenerator):
    """Uses local Ollama LLM to intelligently split and prompt scenes."""

    def __init__(self, model: str = "mistral"):
        self.model = model
        self.api_url = "http://localhost:11434/api/generate"

    def generate(self, story: str, style: str) -> List[Dict]:
        import requests

        prompt = f"""Split this story into 4-8 visual scenes for a cartoon video.
For each scene provide:
- narration: the text to be spoken
- image_prompt: a detailed visual description for image generation ({style} style)
- emotion: one of [happy, sad, angry, scared, peaceful, neutral]
- motion: one of [zoom_in, zoom_out, pan_left, pan_right, ken_burns]

Story: {story}

Respond ONLY with valid JSON array. Each element must have: narration, image_prompt, emotion, motion.
"""
        try:
            resp = requests.post(self.api_url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }, timeout=120)

            result = resp.json()["response"]
            scenes = json.loads(result)

            if isinstance(scenes, dict) and "scenes" in scenes:
                scenes = scenes["scenes"]

            # Add seeds and indices
            for i, scene in enumerate(scenes):
                scene["scene_index"] = i
                scene["seed"] = int(hashlib.md5(f"scene_{i}".encode()).hexdigest()[:8], 16) % 2**32
                scene["duration"] = None

            return scenes
        except Exception as e:
            # Fallback to rule-based
            print(f"LLM failed ({e}), falling back to rule-based")
            return RuleBasedSceneGenerator().generate(story, style)
