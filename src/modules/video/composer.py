"""Video Composer - cinematic transitions, intro/outro, professional output."""
import subprocess
from pathlib import Path
from typing import List, Dict
from src.core.interfaces import BaseComposer
from src.core.config import Config


class FFmpegComposer(BaseComposer):
    """Composes final video with smooth cinematic transitions."""

    # Different transition effects to cycle through
    TRANSITIONS = [
        "fade",
        "fadeblack",
        "dissolve",
        "smoothleft",
        "smoothright",
        "circleopen",
        "slideright",
        "slideleft",
    ]

    def __init__(self, config: Config):
        self.config = config

    def compose(self, scenes: List[Dict], job_id: str) -> str:
        output_path = self.config.output_dir / f"{job_id}_final.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        clips = [s["video_clip_path"] for s in scenes if s.get("video_clip_path")]

        if len(clips) == 0:
            raise RuntimeError("No clips to compose")

        if len(clips) == 1:
            # Add fade in/out to single clip
            return self._add_fade_single(clips[0], output_path)

        # Try crossfade with varied transitions
        transition_dur = self.config.transition_duration

        try:
            filter_complex = self._build_varied_transitions(clips, transition_dur)
            if filter_complex:
                cmd = ["ffmpeg", "-y"]
                for clip in clips:
                    cmd.extend(["-i", clip])

                cmd.extend([
                    "-filter_complex", filter_complex,
                    "-map", "[vout]",
                    "-map", "[aout]",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "medium",
                    "-crf", "20",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-r", str(self.config.video_fps),
                    "-movflags", "+faststart",
                    str(output_path)
                ])

                result = subprocess.run(cmd, capture_output=True, timeout=900)
                if result.returncode == 0:
                    return str(output_path)
        except Exception:
            pass

        # Fallback to simple concat with fade between clips
        return self._concat_with_fade(clips, output_path)

    def _build_varied_transitions(self, clips: List[str], transition_dur: float) -> str:
        """Build filter with different transition types between each scene."""
        n = len(clips)
        if n > 8:
            return ""

        durations = [self._get_duration(c) for c in clips]

        # Video transitions
        video_filters = []
        audio_filters = []

        if n == 2:
            offset = durations[0] - transition_dur
            trans = self.TRANSITIONS[0]
            video_filters.append(f"[0:v][1:v]xfade=transition={trans}:duration={transition_dur}:offset={offset:.2f}[vout]")
            audio_filters.append(f"[0:a][1:a]acrossfade=d={transition_dur}[aout]")
        else:
            # Chain transitions with different effects
            prev_v = "[0:v]"
            prev_a = "[0:a]"
            cumulative_offset = 0

            for i in range(1, n):
                out_v = "[vout]" if i == n - 1 else f"[v{i}]"
                out_a = "[aout]" if i == n - 1 else f"[a{i}]"
                cumulative_offset += durations[i-1] - transition_dur

                # Pick different transition for each scene change
                trans = self.TRANSITIONS[i % len(self.TRANSITIONS)]

                video_filters.append(
                    f"{prev_v}[{i}:v]xfade=transition={trans}:duration={transition_dur}:offset={cumulative_offset:.2f}{out_v}"
                )
                audio_filters.append(
                    f"{prev_a}[{i}:a]acrossfade=d={transition_dur}{out_a}"
                )

                if i < n - 1:
                    prev_v = f"[v{i}]"
                    prev_a = f"[a{i}]"

        return ";".join(video_filters + audio_filters)

    def _concat_with_fade(self, clips: List[str], output_path: Path) -> str:
        """Fallback: concat clips with fade-in/fade-out on each."""
        # Re-encode each clip with fade, then concat
        faded_clips = []
        for i, clip in enumerate(clips):
            faded = self.config.temp_dir / f"faded_{i:03d}.mp4"
            duration = self._get_duration(clip)
            fade_dur = min(0.5, duration / 4)

            cmd = [
                "ffmpeg", "-y", "-i", clip,
                "-vf", f"fade=t=in:st=0:d={fade_dur},fade=t=out:st={duration-fade_dur}:d={fade_dur}",
                "-af", f"afade=t=in:st=0:d={fade_dur},afade=t=out:st={duration-fade_dur}:d={fade_dur}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "fast", "-crf", "20",
                "-c:a", "aac",
                str(faded)
            ]
            subprocess.run(cmd, capture_output=True, timeout=120)
            faded_clips.append(str(faded))

        # Concat all faded clips
        concat_file = self.config.temp_dir / "concat_list.txt"
        with open(concat_file, 'w') as f:
            for clip in faded_clips:
                f.write(f"file '{clip}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, timeout=600)
        return str(output_path)

    def _add_fade_single(self, clip: str, output_path: Path) -> str:
        """Add fade in/out to a single clip."""
        duration = self._get_duration(clip)
        cmd = [
            "ffmpeg", "-y", "-i", clip,
            "-vf", f"fade=t=in:st=0:d=1,fade=t=out:st={duration-1}:d=1",
            "-af", f"afade=t=in:st=0:d=1,afade=t=out:st={duration-1}:d=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", "20",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)
        return str(output_path)

    def _get_duration(self, path: str) -> float:
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
