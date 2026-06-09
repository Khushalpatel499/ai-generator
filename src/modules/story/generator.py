"""Story Generator Module - creates full stories from short ideas using local LLM."""
import json
import requests
from typing import Optional


class StoryGenerator:
    """Generates full stories from brief ideas/topics using Ollama (free local LLM)."""

    TEMPLATES = {
        "cartoon": "Write a fun, visual cartoon story for kids (300-500 words). Include vivid scene descriptions, colorful characters, and a happy ending.",
        "motivation": "Write an inspiring motivational story (300-500 words). Include struggle, perseverance, and triumph. Make it emotionally powerful with vivid imagery.",
        "funny": "Write a hilarious short story (300-500 words). Include absurd situations, witty dialogue, and unexpected punchlines. Keep it family-friendly.",
        "horror": "Write a creepy short horror story (300-500 words). Build tension slowly, use atmospheric descriptions, and end with a twist.",
        "educational": "Write an educational story (300-500 words) that teaches a concept through narrative. Make it engaging with relatable characters.",
    }

    def __init__(self, model: str = "mistral", api_url: str = "http://localhost:11434/api/generate"):
        self.model = model
        self.api_url = api_url

    def generate(self, idea: str, content_type: str = "cartoon", word_count: int = 400) -> str:
        """Generate a full story from a brief idea.

        Args:
            idea: Brief concept like "a robot who learns to dance"
            content_type: cartoon, motivation, funny, horror, educational
            word_count: Target length

        Returns:
            Full story text
        """
        template = self.TEMPLATES.get(content_type, self.TEMPLATES["cartoon"])

        prompt = f"""{template}

Topic/Idea: {idea}
Target length: {word_count} words.

Write ONLY the story. No titles, no notes, no explanations. Start directly with the narrative."""

        try:
            resp = requests.post(self.api_url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }, timeout=180)

            if resp.status_code == 200:
                return resp.json()["response"].strip()
            else:
                raise RuntimeError(f"Ollama returned {resp.status_code}")

        except requests.ConnectionError:
            raise RuntimeError(
                "Ollama not running. Install: curl -fsSL https://ollama.ai/install.sh | sh && ollama pull mistral"
            )

    def generate_from_template(self, idea: str, content_type: str = "cartoon") -> str:
        """Fallback: rule-based story expansion when no LLM available."""
        templates = {
            "cartoon": (
                f"Once upon a time, {idea}. "
                f"The adventure began on a bright sunny morning. "
                f"Our hero faced many challenges along the way. "
                f"But with courage and friendship, everything worked out. "
                f"And they all lived happily ever after."
            ),
            "motivation": (
                f"There was someone who dreamed of {idea}. "
                f"Everyone said it was impossible. They faced failure after failure. "
                f"But they refused to give up. Day after day, they kept pushing forward. "
                f"And finally, against all odds, they achieved what no one thought possible. "
                f"The lesson: your dreams are valid. Never stop believing."
            ),
            "funny": (
                f"So this is the story about {idea}. "
                f"It started normally enough, but then everything went hilariously wrong. "
                f"Nobody expected what happened next. It was chaos, pure chaos. "
                f"In the end, everyone was laughing so hard they couldn't breathe. "
                f"And that's why we don't talk about Tuesdays anymore."
            ),
        }
        return templates.get(content_type, templates["cartoon"])
