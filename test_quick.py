"""Quick test - validates the pipeline without FFmpeg/GPU/LLM."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import Config
from src.pipeline.orchestrator import Pipeline, Job
from src.modules.scene.generator import RuleBasedSceneGenerator
from src.modules.image.generator import DummyImageGenerator
from src.modules.tts.engine import DummyTTSEngine
from src.modules.video.subtitles import SubtitleGenerator
from src.modules.storage.local import LocalStorage


class DummyAnimator:
    """Skip FFmpeg - just copy image path as clip."""
    def animate(self, image_path, audio_path, motion="zoom_in", scene_index=0):
        return image_path  # Pretend image IS the clip


class DummyComposer:
    """Skip FFmpeg - just return first clip path."""
    def __init__(self, config):
        self.config = config

    def compose(self, scenes, job_id):
        # Create a dummy output file
        out = self.config.output_dir / f"{job_id}_final.mp4"
        out.write_text("dummy video file")
        return str(out)


def test_pipeline():
    config = Config()
    config.ensure_dirs()

    pipeline = Pipeline(
        scene_gen=RuleBasedSceneGenerator(),
        image_gen=DummyImageGenerator(config),
        tts_engine=DummyTTSEngine(config),
        animator=DummyAnimator(),
        composer=DummyComposer(config),
        storage=LocalStorage(config),
        subtitle_gen=SubtitleGenerator(),
    )

    story = """A brave little robot named Bolt lived in a junkyard at the edge of the city.
Every night, he would look up at the stars and dream of flying.

One day, he found a broken rocket ship buried under old car parts.
He spent weeks repairing it, using spare gears and colorful wires.

Finally, the day came. Bolt climbed into the rocket and pressed the big red button.
He soared into the sky, leaving a trail of rainbow sparks behind him.

He flew past the clouds, past the birds, all the way to the moon.
And there, standing on the silver surface, Bolt finally felt free."""

    job = Job(story=story, style="cartoon", content_type="cartoon", subtitles=False)

    print("=" * 60)
    print("TESTING AI VIDEO GENERATOR PIPELINE")
    print("=" * 60)
    print(f"\nStory: {len(story)} chars")
    print(f"Style: {job.style}")
    print(f"Job ID: {job.id}")

    result = pipeline.run(job)

    print(f"\n{'=' * 60}")
    if result.status.value == "completed":
        print(f"[PASS] PIPELINE TEST PASSED!")
        print(f"\nResults:")
        print(f"   Status: {result.status.value}")
        print(f"   Scenes generated: {len(result.scenes)}")
        print(f"   Output: {result.output_path}")

        print(f"\nScene Breakdown:")
        for i, scene in enumerate(result.scenes):
            print(f"\n   Scene {i+1}:")
            print(f"     Narration: {scene['narration'][:80]}...")
            print(f"     Emotion: {scene['emotion']}")
            print(f"     Motion: {scene['motion']}")
            print(f"     Image: {scene.get('image_path', 'N/A')}")
            print(f"     Audio: {scene.get('audio_path', 'N/A')}")

        # Test subtitle generation
        print(f"\nTesting Subtitle Generation...")
        sub_gen = SubtitleGenerator()
        srt_path = str(config.temp_dir / "test_subs.srt")
        sub_gen.generate_srt(result.scenes, srt_path)
        srt_content = Path(srt_path).read_text()
        print(f"   SRT file created: {srt_path}")
        print(f"   Preview:\n{srt_content[:300]}...")

        print(f"\n{'=' * 60}")
        print("[PASS] ALL TESTS PASSED - Pipeline is working!")
        print(f"\nNext steps to get REAL video output:")
        print(f"   1. Install FFmpeg: https://ffmpeg.org/download.html")
        print(f"   2. Add to PATH, then run:")
        print(f"      python -m src.cli --story story.txt --style cartoon")
        print(f"   3. For real images, add GPU + run:")
        print(f"      pip install diffusers torch")
        print(f"      python -m src.cli --story story.txt --use-gpu")
    else:
        print(f"[FAIL] PIPELINE TEST FAILED!")
        print(f"   Error: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    test_pipeline()
