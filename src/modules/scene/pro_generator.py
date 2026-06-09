"""Professional Scene Generator - YouTube-quality prompts with exact scene control."""
import hashlib
from typing import List, Dict
from src.core.interfaces import BaseSceneGenerator


class ProSceneGenerator(BaseSceneGenerator):
    """Takes structured story with scene breakdown and generates pro-quality prompts."""

    # Character visual descriptions - SAME across all scenes for consistency
    CHARACTER_STYLES = {
        "cartoon": {
            "milo": "small cute orange tabby cat with big green eyes, fluffy tail, expressive face",
            "elder_owl": "wise old brown owl with spectacles, white chest feathers, sitting on branch",
            "storm_spirit": "menacing dark purple cloud creature with glowing red eyes, swirling darkness, lightning",
        },
        "anime": {
            "milo": "cute chibi orange cat, anime style, big sparkling eyes, small body",
            "elder_owl": "mystical wise owl, anime style, golden eyes, ancient aura",
            "storm_spirit": "dark demon cloud, anime villain, red glowing eyes, purple lightning",
        },
        "pixar": {
            "milo": "adorable orange kitten, Pixar 3D style, big expressive eyes, soft fur texture",
            "elder_owl": "elderly wise owl, Pixar 3D, warm eyes, detailed feathers",
            "storm_spirit": "terrifying storm monster, Pixar villain, dark swirling clouds, red eyes",
        },
    }

    def generate(self, story: str, style: str) -> List[Dict]:
        """Parse structured story and generate optimized scenes."""
        # Check if story has structured scene markers
        if "Scene" in story or "scene" in story:
            return self._parse_structured_story(story, style)
        else:
            return self._auto_split_story(story, style)

    def _parse_structured_story(self, story: str, style: str) -> List[Dict]:
        """Parse a story with scene markers."""
        import re

        scenes = []
        # Find scene blocks
        scene_blocks = re.split(r'(?:Scene\s*\d+|🟡\s*Scene\s*\d+)[:\s]*', story, flags=re.IGNORECASE)
        scene_blocks = [b.strip() for b in scene_blocks if b.strip() and len(b.strip()) > 20]

        for i, block in enumerate(scene_blocks):
            # Extract visual, dialogue, emotion from block
            visual = self._extract_field(block, "Visual")
            dialogue = self._extract_field(block, "Dialogue") or self._extract_field(block, "Narration")
            emotion = self._extract_field(block, "Emotion") or "neutral"

            # If no structured fields, use whole block
            if not visual and not dialogue:
                narration = block[:200]
                visual = block[:150]
            else:
                narration = dialogue or visual

            # Clean emotion
            emotion = self._normalize_emotion(emotion)
            motion = self._emotion_to_motion(emotion, i, len(scene_blocks))

            # Build PERFECT image prompt
            image_prompt = self._build_pro_prompt(visual, style, emotion, i, len(scene_blocks))

            # Consistent seed per character
            seed = int(hashlib.md5(f"milo_scene_{i}".encode()).hexdigest()[:8], 16) % 2**32

            scenes.append({
                "scene_index": i,
                "narration": narration.strip(),
                "image_prompt": image_prompt,
                "emotion": emotion,
                "motion": motion,
                "seed": seed,
                "duration": None,
            })

        return scenes

    def _auto_split_story(self, story: str, style: str) -> List[Dict]:
        """Auto-split plain story text into scenes."""
        import re

        paragraphs = [p.strip() for p in story.split("\n\n") if p.strip() and len(p.strip()) > 30]

        if len(paragraphs) <= 2:
            sentences = re.split(r'(?<=[.!?])\s+', story.strip())
            paragraphs = []
            for i in range(0, len(sentences), 2):
                para = " ".join(sentences[i:i+2])
                if len(para) > 20:
                    paragraphs.append(para)

        scenes = []
        for i, para in enumerate(paragraphs):
            emotion = self._detect_emotion(para)
            motion = self._emotion_to_motion(emotion, i, len(paragraphs))
            seed = int(hashlib.md5(f"scene_{i}".encode()).hexdigest()[:8], 16) % 2**32

            scenes.append({
                "scene_index": i,
                "narration": para,
                "image_prompt": self._build_pro_prompt(para, style, emotion, i, len(paragraphs)),
                "emotion": emotion,
                "motion": motion,
                "seed": seed,
                "duration": None,
            })

        return scenes

    def _build_pro_prompt(self, visual_desc: str, style: str, emotion: str,
                          scene_idx: int, total: int) -> str:
        """Build YouTube-quality image generation prompt."""

        # Camera angles that tell the story
        if scene_idx == 0:
            camera = "wide establishing shot, aerial view"
        elif scene_idx == total - 1:
            camera = "wide cinematic shot, golden hour"
        elif emotion in ("scared", "angry"):
            camera = "dramatic low angle shot, intense"
        elif emotion == "epic":
            camera = "epic hero shot, low angle, dramatic"
        elif emotion == "peaceful":
            camera = "wide beautiful landscape shot"
        else:
            cameras = ["medium close-up shot", "over the shoulder shot",
                      "dynamic angle shot", "cinematic medium shot"]
            camera = cameras[scene_idx % len(cameras)]

        # Lighting based on emotion
        lighting_map = {
            "happy": "warm golden sunlight, lens flare, vibrant colors",
            "sad": "blue hour lighting, overcast, muted tones, rain",
            "angry": "dramatic red-orange lighting, fire glow, high contrast",
            "scared": "dark ominous lighting, deep shadows, moonlight, fog, eerie",
            "peaceful": "soft morning light, pastel colors, warm glow",
            "epic": "dramatic backlight, volumetric god rays, epic sunset",
            "neutral": "soft natural daylight, balanced colors",
        }
        lighting = lighting_map.get(emotion, lighting_map["neutral"])

        # Environment/atmosphere
        atmosphere_map = {
            "happy": "butterflies, flowers blooming, sparkles",
            "sad": "falling leaves, grey sky, puddles",
            "angry": "storm clouds, lightning bolts, destruction",
            "scared": "dark forest, twisted shadows, glowing eyes in darkness",
            "peaceful": "cherry blossoms, gentle breeze, birds flying",
            "epic": "rays of light breaking through clouds, magical particles",
            "neutral": "detailed background, lush nature",
        }
        atmosphere = atmosphere_map.get(emotion, "")

        # Style-specific quality tags
        style_tags = {
            "cartoon": "Disney Pixar style, vibrant saturated colors, clean smooth lines, professional 2D animation quality, detailed expressive characters, rich background art",
            "anime": "Studio Ghibli anime style, beautiful watercolor background, cel shading, makoto shinkai lighting, detailed anime art, 4k",
            "pixar": "Pixar 3D render, subsurface scattering, ray tracing, octane render, hyperrealistic 3D cartoon, cinema quality",
            "comic": "Marvel comic book art, bold ink outlines, dynamic composition, vibrant pop colors, action splash page",
        }
        style_tag = style_tags.get(style, style_tags["cartoon"])

        # Clean visual description
        visual_clean = visual_desc[:150].strip()
        # Remove metadata like "Emotion:", "Visual:" etc
        import re
        visual_clean = re.sub(r'(Emotion|Dialogue|Visual|Narration)\s*:', '', visual_clean).strip()

        prompt = (
            f"{visual_clean}, "
            f"{camera}, "
            f"{lighting}, "
            f"{atmosphere}, "
            f"{style_tag}, "
            f"masterpiece, best quality, ultra detailed, sharp focus, "
            f"cinematic composition, professional illustration, trending on artstation"
        )

        return prompt

    def _extract_field(self, block: str, field_name: str) -> str:
        """Extract a field value from scene block."""
        import re
        pattern = rf'{field_name}\s*:\s*(.+?)(?:\n|$)'
        match = re.search(pattern, block, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Remove markdown/emoji
            value = re.sub(r'[🟡🎬🎭📖]', '', value).strip()
            # Remove parenthetical directions
            value = re.sub(r'\([^)]*\)', '', value).strip()
            return value
        return ""

    def _normalize_emotion(self, emotion: str) -> str:
        """Normalize emotion string to supported values."""
        emotion = emotion.lower().strip()
        mapping = {
            "calm": "peaceful",
            "serious": "neutral",
            "fear": "scared",
            "evil": "angry",
            "intense": "angry",
            "curious": "neutral",
            "brave": "epic",
            "powerful": "epic",
            "hope": "epic",
            "victory": "happy",
            "inspirational": "happy",
            "lonely": "sad",
        }
        # Check direct match
        if emotion in ("happy", "sad", "angry", "scared", "peaceful", "epic", "neutral"):
            return emotion
        # Check mapping
        for key, val in mapping.items():
            if key in emotion:
                return val
        return "neutral"

    def _emotion_to_motion(self, emotion: str, scene_idx: int, total: int) -> str:
        """Pick motion effect based on emotion + story position."""
        if scene_idx == 0:
            return "ken_burns"  # Establishing shot always ken burns
        if scene_idx == total - 1:
            return "zoom_out"  # Ending always zooms out

        motion_map = {
            "happy": "zoom_in",
            "sad": "zoom_out",
            "angry": "pan_left",
            "scared": "pan_right",
            "peaceful": "ken_burns",
            "epic": "zoom_in_top",
            "neutral": "pan_down",
        }
        return motion_map.get(emotion, "ken_burns")

    def _detect_emotion(self, text: str) -> str:
        """Detect emotion from text content."""
        text_lower = text.lower()
        emotions = {
            "happy": ["happy", "joy", "laugh", "smile", "cheer", "celebrate", "sunny", "bright"],
            "sad": ["sad", "cry", "tears", "lonely", "lost", "broken", "rain"],
            "angry": ["angry", "destroy", "fight", "storm", "rage", "dark", "evil"],
            "scared": ["scared", "fear", "panic", "run", "danger", "tremble", "dark"],
            "peaceful": ["peace", "calm", "quiet", "gentle", "soft", "harmony"],
            "epic": ["hero", "brave", "courage", "power", "rise", "finally", "victory", "save"],
        }
        scores = {e: sum(1 for kw in kws if kw in text_lower) for e, kws in emotions.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "neutral"
