"""Video Composer - stitches scene clips with transitions into final MP4."""
import subprocess
from pathlib import Path
from typing import List, Dict
from src.core.interfaces import BaseComposer
from src.core.config import Config


class FFmpegComposer(BaseComposer):
    """Composes final video using FFmpeg concat with crossfade transitions."""

    def __init__(self, config: Config):
        self.config = config

    def compose(self, scenes: List[Dict], job_id: str) -> str:
        output_path = self.config.output_dir / f"{job_id}_final.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        clips = [s["video_clip_path"] for s in scenes if s.get("video_clip_path")]

        if len(clips) == 0:
            raise RuntimeError("No clips to compose")

        if len(clips) == 1:
            # Single clip, just copy
            subprocess.run(["ffmpeg", "-y", "-i", clips[0], "-c", "copy", str(output_path)],
                          capture_output=True, timeout=120)
            return str(output_path)

        # Use concat with crossfade transitions
        transition_dur = self.config.transition_duration

        # Build complex filter for crossfade between clips
        filter_complex = self._build_crossfade_filter(clips, transition_dur)

        if filter_complex:
            # Complex crossfade approach
            cmd = ["ffmpeg", "-y"]
            for clip in clips:
                cmd.extend(["-i", clip])

            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-map", "[aout]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-r", str(self.config.video_fps),
                str(output_path)
            ])
        else:
            # Simple concat (fallback for many clips)
            cmd = self._build_concat_cmd(clips, output_path)

        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode != 0:
            # Fallback to simple concat
            return self._simple_concat(clips, output_path)

        return str(output_path)

    def _build_crossfade_filter(self, clips: List[str], transition_dur: float) -> str:
        """Build FFmpeg xfade filter chain for 2-6 clips."""
        n = len(clips)
        if n > 6:
            return ""  # Too complex, use concat fallback

        # Get durations
        durations = [self._get_duration(c) for c in clips]

        filters = []
        offsets = []

        # Calculate offsets (when each transition starts)
        cumulative = 0
        for i in range(n - 1):
            cumulative += durations[i] - transition_dur
            offsets.append(cumulative)

        # Video crossfade chain
        if n == 2:
            filters.append(f"[0:v][1:v]xfade=transition=fade:duration={transition_dur}:offset={offsets[0]}[vout]")
            filters.append(f"[0:a][1:a]acrossfade=d={transition_dur}[aout]")
        else:
            # Chain xfades
            prev_v = "[0:v]"
            prev_a = "[0:a]"
            for i in range(1, n):
                out_v = "[vout]" if i == n - 1 else f"[v{i}]"
                out_a = "[aout]" if i == n - 1 else f"[a{i}]"
                offset = sum(durations[:i]) - transition_dur * i
                filters.append(f"{prev_v}[{i}:v]xfade=transition=fade:duration={transition_dur}:offset={offset:.2f}{out_v}")
                filters.append(f"{prev_a}[{i}:a]acrossfade=d={transition_dur}{out_a}")
                prev_v = out_v if i < n - 1 else prev_v
                prev_a = out_a if i < n - 1 else prev_a

        return ";".join(filters)

    def _simple_concat(self, clips: List[str], output_path: Path) -> str:
        """Fallback: simple concat without transitions."""
        concat_file = self.config.temp_dir / "concat_list.txt"
        with open(concat_file, 'w') as f:
            for clip in clips:
                f.write(f"file '{clip}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, timeout=600)
        return str(output_path)

    def _build_concat_cmd(self, clips, output_path):
        concat_file = self.config.temp_dir / "concat_list.txt"
        with open(concat_file, 'w') as f:
            for clip in clips:
                f.write(f"file '{clip}'\n")
        return [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file), "-c", "copy", str(output_path)
        ]

    def _get_duration(self, path: str) -> float:
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
