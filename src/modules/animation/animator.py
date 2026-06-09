"""Animation Layer - applies Ken Burns, zoom, pan effects to static images."""
import subprocess
from pathlib import Path
from src.core.interfaces import BaseAnimator
from src.core.config import Config


class FFmpegAnimator(BaseAnimator):
    """Applies motion effects using FFmpeg's zoompan filter."""

    def __init__(self, config: Config):
        self.config = config

    def animate(self, image_path: str, audio_path: str, motion: str = "zoom_in", scene_index: int = 0) -> str:
        output_path = self.config.temp_dir / f"clip_{scene_index:03d}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get audio duration
        duration = self._get_audio_duration(audio_path)
        fps = self.config.video_fps
        total_frames = int(duration * fps)

        # Build zoompan filter based on motion type
        w, h = self.config.video_resolution
        zoompan_filter = self._build_zoompan(motion, total_frames, fps, w, h)

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-filter_complex",
            f"[0:v]{zoompan_filter},format=yuv420p[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-t", str(duration),
            "-movflags", "+faststart",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg animation failed: {result.stderr.decode()[-500:]}")

        return str(output_path)

    def _build_zoompan(self, motion: str, total_frames: int, fps: int, w: int, h: int) -> str:
        d = total_frames
        presets = self.config.motion_presets.get(motion, self.config.motion_presets["zoom_in"])

        if motion == "zoom_in":
            return f"zoompan=z='min(zoom+0.001,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s={w}x{h}:fps={fps}"
        elif motion == "zoom_out":
            return f"zoompan=z='if(eq(on,1),1.2,max(zoom-0.001,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s={w}x{h}:fps={fps}"
        elif motion == "pan_left":
            return f"zoompan=z='1.1':x='iw/2-(iw/zoom/2)+on*2':y='ih/2-(ih/zoom/2)':d={d}:s={w}x{h}:fps={fps}"
        elif motion == "pan_right":
            return f"zoompan=z='1.1':x='iw/2-(iw/zoom/2)-on*2':y='ih/2-(ih/zoom/2)':d={d}:s={w}x{h}:fps={fps}"
        elif motion == "ken_burns":
            return f"zoompan=z='min(zoom+0.0008,1.15)':x='iw/2-(iw/zoom/2)+on':y='ih/2-(ih/zoom/2)':d={d}:s={w}x{h}:fps={fps}"
        else:
            return f"zoompan=z='1':d={d}:s={w}x{h}:fps={fps}"

    def _get_audio_duration(self, audio_path: str) -> float:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
