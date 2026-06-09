"""Enhanced Scene Generator - better prompts, cinematic quality."""
import json
import re
import hashlib
from typing import List, Dict
from src.core.interfaces import BaseSceneGenerator
from src.modules.image.characters import CharacterManager


class EnhancedSceneGenerator(BaseSceneGenerator):
    """Produces cinematic, high-quality image prompts with character consistency."""

    EMOTION_KEYWORDS = {
        "happy": ["happy", "joy", "laugh", "smile", "celebrate", "excited", "love", "bright", "wonderful"],
        "sad": ["sad", "cry", "tears", "lonely", "grief", "miss", "lost", "broken"],
        "angry": ["angry", "fury", "rage", "shout", "fight", "battle", "destroy"],
        "scared": ["scared", "fear", "dark", "horror", "tremble", "shadow", "danger"],
        "peaceful": ["calm", "peace", "quiet", "serene", "gentle", "soft", "rest", "sleep"],
        "epic": ["finally", "soar", "flew", "hero", "triumph", "victory", "rise", "power"],
    }

    MOTION_MAP = {
        "happy": "zoom_in",
        "sad": "zoom_out",
        "angry": "pan_left",
        "scared": "pan_right",
        "peaceful": "ken_burns",
        "epic": "zoom_in_top",
        "neutral": "pan_down",
    }

    CINEMATIC_ANGLES = [
        "wide shot",
        "close-up shot",
        "medium shot",
        "establishing shot",
        "dramatic low angle",
        "bird's eye view",
    ]

    LIGHTING_MAP = {
        "happy": "warm golden hour lighting, sun rays",
        "sad": "overcast, blue tones, soft shadows",
        "angry": "dramatic red lighting, high contrast",
        "scared": "dark moody lighting, deep shadows, fog",
        "peaceful": "soft pastel lighting, gentle sunset",
        "epic": "cinematic dramatic lighting, volumetric rays",
        "neutral": "natural balanced lighting",
    }

    def __init__(self):
        self.char_manager = CharacterManager()

    def generate(self, story: str, style: str) -> List[Dict]:
        # Auto-detect characters
        self.char_manager.auto_detect_and_register(story)

        paragraphs = [p.strip() for p in story.split("\n\n") if p.strip()]

        if len(paragraphs) <= 1:
            sentences = re.split(r'(?<=[.!?])\s+', story.strip())
            paragraphs = []
            for i in range(0, len(sentences), 2):  # 2 sentences per scene for more scenes
                paragraphs.append(" ".join(sentences[i:i+2]))

        scenes = []
        for i, para in enumerate(paragraphs):
            emotion = self._detect_emotion(para)
            seed = self.char_manager.get_seed_for_scene(para)
            if seed is None:
                seed = int(hashlib.md5(f"scene_{i}".encode()).hexdigest()[:8], 16) % 2**32

            image_prompt = self._build_cinematic_prompt(para, style, emotion, i, len(paragraphs))

            scenes.append({
                "scene_index": i,
                "narration": para,
                "image_prompt": image_prompt,
                "emotion": emotion,
                "motion": self.MOTION_MAP.get(emotion, "zoom_in"),
                "seed": seed,
                "duration": None,
            })

        return scenes

    def _detect_emotion(self, text: str) -> str:
        text_lower = text.lower()
        scores = {}
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            scores[emotion] = sum(1 for kw in keywords if kw in text_lower)
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "neutral"

    def _build_cinematic_prompt(self, narration: str, style: str, emotion: str,
                                 scene_idx: int, total_scenes: int) -> str:
        # Remove dialogue
        visual = re.sub(r'"[^"]*"', '', narration)
        visual = visual[:150].strip()

        # Pick camera angle based on position in story
        if scene_idx == 0:
            angle = "establishing wide shot"
        elif scene_idx == total_scenes - 1:
            angle = "cinematic wide shot"
        else:
            angle = self.CINEMATIC_ANGLES[scene_idx % len(self.CINEMATIC_ANGLES)]

        # Get lighting for emotion
        lighting = self.LIGHTING_MAP.get(emotion, self.LIGHTING_MAP["neutral"])

        # Character consistency
        visual = self.char_manager.enhance_prompt(visual, narration)

        # Build final cinematic prompt
        prompt = (
            f"{visual}, "
            f"{angle}, "
            f"{lighting}, "
            f"masterpiece, best quality, highly detailed, "
            f"sharp focus, 4k, cinematic composition, "
            f"professional illustration"
        )

        return prompt
