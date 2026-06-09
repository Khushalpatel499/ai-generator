"""Character Manager - maintains consistent characters across scenes."""
from typing import Dict, List, Optional
import hashlib


class CharacterManager:
    """Manages character descriptions and seeds for consistency across scenes."""

    def __init__(self):
        self.characters: Dict[str, dict] = {}

    def register(self, name: str, description: str, seed: Optional[int] = None):
        """Register a character with visual description."""
        if seed is None:
            seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 2**32
        self.characters[name.lower()] = {
            "name": name,
            "description": description,
            "seed": seed,
        }

    def auto_detect_and_register(self, story: str):
        """Auto-detect characters from story and create consistent descriptions."""
        import re
        # Find capitalized names that appear multiple times
        words = re.findall(r'\b([A-Z][a-z]{2,})\b', story)
        # Filter common words
        skip = {"The", "One", "Every", "Finally", "And", "But", "His", "Her", "She", "He"}
        candidates = [w for w in words if w not in skip]

        # Count occurrences
        from collections import Counter
        counts = Counter(candidates)
        characters = [name for name, count in counts.items() if count >= 2]

        for name in characters[:5]:  # Max 5 characters
            self.register(name, self._generate_description(name, story))

    def _generate_description(self, name: str, story: str) -> str:
        """Extract/generate visual description for a character from context."""
        import re
        # Look for descriptions near the character name
        patterns = [
            rf'{name}\s+(?:was|is)\s+(?:a\s+)?(.{{10,60}}?)[.\n]',
            rf'(?:the|a)\s+(.{{5,30}}?)\s+(?:named|called)\s+{name}',
            rf'{name},?\s+(?:the|a)\s+(.{{5,40}}?)[,.\n]',
        ]
        for pattern in patterns:
            match = re.search(pattern, story, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return f"character named {name}"

    def enhance_prompt(self, prompt: str, scene_narration: str) -> str:
        """Add character descriptions to image prompt for consistency."""
        additions = []
        for key, char in self.characters.items():
            if key in scene_narration.lower():
                additions.append(char["description"])

        if additions:
            char_desc = ", ".join(additions)
            return f"{char_desc}, {prompt}"
        return prompt

    def get_seed_for_scene(self, scene_narration: str) -> Optional[int]:
        """Get consistent seed based on which characters appear in scene."""
        for key, char in self.characters.items():
            if key in scene_narration.lower():
                return char["seed"]
        return None
