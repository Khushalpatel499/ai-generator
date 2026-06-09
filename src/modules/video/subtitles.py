"""Subtitle Generator - creates SRT subtitles and burns them into video."""
import re
from pathlib import Path
from typing import List, Dict


class SubtitleGenerator:
    """Generates SRT subtitle files from scene narrations and burns into video."""

    def generate_srt(self, scenes: List[Dict], output_path: str) -> str:
        """Create SRT file from scenes with estimated timings."""
        srt_lines = []
        current_time = 0.0

        for i, scene in enumerate(scenes):
            narration = scene["narration"]
            # Estimate duration from word count (~150 wpm)
            duration = scene.get("duration") or max(2.0, len(narration.split()) / 2.5)

            # Split long narrations into subtitle chunks (max 10 words per line)
            chunks = self._split_into_chunks(narration, max_words=10)
            chunk_duration = duration / len(chunks)

            for j, chunk in enumerate(chunks):
                start = current_time + (j * chunk_duration)
                end = start + chunk_duration
                srt_lines.append(self._format_srt_entry(len(srt_lines) + 1, start, end, chunk))

            current_time += duration

        srt_content = "\n".join(srt_lines)
        Path(output_path).write_text(srt_content, encoding="utf-8")
        return output_path

    def _split_into_chunks(self, text: str, max_words: int = 10) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), max_words):
            chunks.append(" ".join(words[i:i + max_words]))
        return chunks or [text]

    def _format_srt_entry(self, index: int, start: float, end: float, text: str) -> str:
        return f"{index}\n{self._format_time(start)} --> {self._format_time(end)}\n{text}\n"

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def burn_subtitles(self, video_path: str, srt_path: str, output_path: str) -> str:
        """Burn subtitles into video using FFmpeg."""
        import subprocess

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=3,Outline=2'",
            "-c:a", "copy",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"Subtitle burn failed: {result.stderr.decode()[-300:]}")
        return output_path
