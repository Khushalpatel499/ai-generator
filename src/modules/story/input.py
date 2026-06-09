"""Story input module - handles text validation and preprocessing."""
import re
from pathlib import Path


class StoryInput:
    """Validates and preprocesses story text."""

    MIN_LENGTH = 50
    MAX_LENGTH = 10000

    def load(self, source: str) -> str:
        path = Path(source)
        if path.exists() and path.suffix in ('.txt', '.md'):
            text = path.read_text(encoding='utf-8')
        else:
            text = source
        return self.validate(text)

    def validate(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        if len(text) < self.MIN_LENGTH:
            raise ValueError(f"Story too short ({len(text)} chars). Min: {self.MIN_LENGTH}")
        if len(text) > self.MAX_LENGTH:
            raise ValueError(f"Story too long ({len(text)} chars). Max: {self.MAX_LENGTH}")
        return text
