"""Animation Layer - CINEMATIC motion effects like real YouTube cartoon videos."""
import subprocess
from pathlib import Path
from src.core.interfaces import BaseAnimator
from src.core.config import Config


class FFmpegAnimator(BaseAnimator):
    """Creates strong, cinematic Ken Burns/zoom/pan animation on images.
    
    Reference: YouTube cartoon story channels use 20-30% zoom with smooth pan.
    This creates the illusion of camera movement within a still frame.
    """

    def __init__(self, config: Config):
        self.config = config

    def animate(self, image_path: str, audio_path: str, motion: str = "zoom_in", scene_index: int = 0) -> str:
        output_path = self.config.temp_dir / f"clip_{scene_index:03d}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        duration = self._get_audio_duration(audio_path)
        fps = self.config.video_fps
        total_frames = int(duration * fps)
        w, h = self.config.video_resolution

        # IMPORTANT: Scale image to 2x resolution first, then zoompan crops from it.
        # This gives room for pan/zoom without hitting edges.
        scale_w = w * 2
        scale_h = h * 2

        zoompan_expr = self._get_motion_expr(motion, total_frames, fps, w, h)

        # The pipeline: scale up -> zoompan (creates the motion) -> output at target res
        filter_chain = (
            f"[0:v]scale={scale_w}:{scale_h}:flags=lanczos,"
            f"zoompan={zoompan_expr},"
            f"format=yuv420p[v]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-filter_complex", filter_chain,
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-t", str(duration),
            "-movflags", "+faststart",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode != 0:
            # Fallback: simpler command
            return self._simple_animate(image_path, audio_path, duration, total_frames, w, h, output_path)

        return str(output_path)

    def _get_motion_expr(self, motion: str, frames: int, fps: int, w: int, h: int) -> str:
        """Generate zoompan expression for different motion types.
        
        Key formula:
        - z = zoom level (1.0 = original, 1.5 = 50% zoomed in)
        - x, y = top-left corner of the visible area
        - d = total number of frames
        - s = output size
        """
        d = frames

        motions = {
            # Smooth zoom in from 1.0x to 1.4x (very visible)
            "zoom_in": (
                f"z='1.0+0.4*on/{d}':"
                f"x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d={d}:s={w}x{h}:fps={fps}"
            ),
            # Zoom out from 1.4x to 1.0x
            "zoom_out": (
                f"z='1.4-0.4*on/{d}':"
                f"x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d={d}:s={w}x{h}:fps={fps}"
            ),
            # Pan from right to left (like camera tracking)
            "pan_left": (
                f"z='1.3':"
                f"x='iw*0.35*(1-on/{d})':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d={d}:s={w}x{h}:fps={fps}"
            ),
            # Pan from left to right
            "pan_right": (
                f"z='1.3':"
                f"x='iw*0.35*on/{d}':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d={d}:s={w}x{h}:fps={fps}"
            ),
            # Classic Ken Burns - slow zoom + gentle horizontal drift
            "ken_burns": (
                f"z='1.0+0.3*on/{d}':"
                f"x='iw*0.05+iw*0.15*on/{d}':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d={d}:s={w}x{h}:fps={fps}"
            ),
            # Zoom into top portion (dramatic for epic moments)
            "zoom_in_top": (
                f"z='1.0+0.5*on/{d}':"
                f"x='iw/2-(iw/zoom/2)':"
                f"y='ih*0.1':"
                f"d={d}:s={w}x{h}:fps={fps}"
            ),
            # Slow pan downward (reveal shot)
            "pan_down": (
                f"z='1.3':"
                f"x='iw/2-(iw/zoom/2)':"
                f"y='ih*0.25*on/{d}':"
                f"d={d}:s={w}x{h}:fps={fps}"
            ),
            # Dramatic zoom + pan combo
            "dramatic": (
                f"z='1.0+0.35*on/{d}':"
                f"x='iw*0.1+iw*0.1*on/{d}':"
                f"y='ih*0.1+ih*0.05*on/{d}':"
                f"d={d}:s={w}x{h}:fps={fps}"
            ),
        }

        return motions.get(motion, motions["ken_burns"])

    def _simple_animate(self, image_path, audio_path, duration, frames, w, h, output_path) -> str:
        """Fallback with simpler filter chain."""
        d = frames
        fps = self.config.video_fps

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-filter_complex",
            f"[0:v]scale={w*2}:{h*2}:flags=lanczos,"
            f"zoompan=z='1.0+0.3*on/{d}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s={w}x{h}:fps={fps},"
            f"format=yuv420p[v]",
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-shortest", "-t", str(duration),
            "-movflags", "+faststart",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, timeout=600)
        return str(output_path)

    def _get_audio_duration(self, audio_path: str) -> float:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
