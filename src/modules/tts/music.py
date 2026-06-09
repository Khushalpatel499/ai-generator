"""Background Music Mixer - adds royalty-free music under narration."""
import subprocess
from pathlib import Path
from typing import Optional


class MusicMixer:
    """Mixes background music at low volume behind narration audio."""

    def __init__(self, music_dir: str = "./assets/music"):
        self.music_dir = Path(music_dir)

    def mix(self, audio_path: str, music_path: Optional[str] = None,
            music_volume: float = 0.12, output_path: Optional[str] = None) -> str:
        """Mix background music under narration.

        Args:
            audio_path: Path to narration WAV
            music_path: Path to background music file (mp3/wav)
            music_volume: Volume of music (0.0 to 1.0), default 0.12 = subtle
            output_path: Where to save mixed audio
        """
        if music_path is None:
            music_path = self._pick_music()

        if music_path is None:
            return audio_path  # No music available, return original

        if output_path is None:
            output_path = audio_path.replace(".wav", "_mixed.wav")

        # Get narration duration
        duration = self._get_duration(audio_path)

        # Mix: narration at full volume + music at low volume, trim to narration length
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-i", music_path,
            "-filter_complex",
            f"[1:a]volume={music_volume},afade=t=in:st=0:d=2,afade=t=out:st={duration-2}:d=2[bg];"
            f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map", "[out]",
            "-c:a", "pcm_s16le",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            return audio_path  # Fallback to original if mixing fails

        return output_path

    def _pick_music(self) -> Optional[str]:
        """Pick a music file from assets/music/ directory."""
        if not self.music_dir.exists():
            return None
        music_files = list(self.music_dir.glob("*.mp3")) + list(self.music_dir.glob("*.wav"))
        if not music_files:
            return None
        return str(music_files[0])  # Use first available

    def pick_by_emotion(self, emotion: str) -> Optional[str]:
        """Pick music matching the scene emotion."""
        if not self.music_dir.exists():
            return None

        # Look for emotion-named files: happy.mp3, sad.mp3, etc.
        for ext in ("mp3", "wav"):
            path = self.music_dir / f"{emotion}.{ext}"
            if path.exists():
                return str(path)

        # Fallback to any available music
        return self._pick_music()

    def _get_duration(self, path: str) -> float:
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
