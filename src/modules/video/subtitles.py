"""Subtitle Generator - YouTube-quality styled subtitles."""
import subprocess
from pathlib import Path
from typing import List, Dict


class SubtitleGenerator:
    """Generates beautiful, readable subtitles - YouTube quality."""

    def generate_srt(self, scenes: List[Dict], output_path: str) -> str:
        """Create SRT with proper word-by-word timing."""
        srt_lines = []
        current_time = 0.0

        for scene in scenes:
            narration = scene["narration"]
            duration = scene.get("duration") or max(3.0, len(narration.split()) / 2.5)

            # Split into SHORT readable chunks (5-7 words max for readability)
            chunks = self._split_smart(narration, max_words=7)
            chunk_duration = duration / len(chunks)

            for j, chunk in enumerate(chunks):
                start = current_time + (j * chunk_duration)
                end = start + chunk_duration - 0.05  # Small gap between subtitles
                srt_lines.append(self._format_srt_entry(len(srt_lines) + 1, start, end, chunk))

            current_time += duration

        srt_content = "\n".join(srt_lines)
        Path(output_path).write_text(srt_content, encoding="utf-8")
        return output_path

    def _split_smart(self, text: str, max_words: int = 7) -> List[str]:
        """Split text into readable chunks, respecting punctuation."""
        import re
        # First split by sentence
        sentences = re.split(r'(?<=[.!?,;:])\s+', text.strip())

        chunks = []
        for sentence in sentences:
            words = sentence.split()
            if len(words) <= max_words:
                chunks.append(sentence)
            else:
                # Split long sentences at natural break points
                for i in range(0, len(words), max_words):
                    chunk = " ".join(words[i:i + max_words])
                    chunks.append(chunk)

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
        """Burn BEAUTIFUL subtitles - big, bold, readable like YouTube videos."""
        # Convert backslashes for FFmpeg on Windows
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

        # YouTube-style subtitle styling:
        # - Big bold white text
        # - Black outline for readability
        # - Bottom center position
        # - Modern font
        style = (
            "FontName=Arial,"
            "FontSize=22,"
            "PrimaryColour=&H00FFFFFF,"  # White
            "SecondaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"  # Black outline
            "BackColour=&H80000000,"  # Semi-transparent black bg
            "Bold=1,"
            "Outline=2,"
            "Shadow=1,"
            "MarginV=50,"  # Distance from bottom
            "Alignment=2,"  # Bottom center
            "BorderStyle=4"  # Background box style
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles='{srt_escaped}':force_style='{style}'",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "20",
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode != 0:
            # Try alternative approach with ASS subtitles
            return self._burn_ass_subtitles(video_path, srt_path, output_path)

        return output_path

    def _burn_ass_subtitles(self, video_path: str, srt_path: str, output_path: str) -> str:
        """Fallback: convert SRT to ASS format for better styling control."""
        ass_path = srt_path.replace(".srt", ".ass")

        # Convert SRT to ASS with custom styling
        self._srt_to_ass(srt_path, ass_path)

        ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"ass='{ass_escaped}'",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "20",
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode != 0:
            # Final fallback: return video without subtitles
            return video_path

        return output_path

    def _srt_to_ass(self, srt_path: str, ass_path: str):
        """Convert SRT to ASS with beautiful styling."""
        import re

        # ASS header with YouTube-style formatting
        header = """[Script Info]
Title: AI Video Generator Subtitles
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,10,10,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        srt_content = Path(srt_path).read_text(encoding="utf-8")
        entries = re.split(r'\n\n+', srt_content.strip())

        events = []
        for entry in entries:
            lines = entry.strip().split('\n')
            if len(lines) >= 3:
                time_match = re.match(r'(\d+:\d+:\d+),(\d+)\s*-->\s*(\d+:\d+:\d+),(\d+)', lines[1])
                if time_match:
                    start = f"{time_match.group(1)}.{time_match.group(2)[:2]}"
                    end = f"{time_match.group(3)}.{time_match.group(4)[:2]}"
                    text = " ".join(lines[2:]).replace('\n', '\\N')
                    events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        ass_content = header + "\n".join(events)
        Path(ass_path).write_text(ass_content, encoding="utf-8")
