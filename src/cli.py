"""CLI entry point - run video generation from command line."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import Config
from src.pipeline.orchestrator import Pipeline, Job
from src.modules.story.generator import StoryGenerator
from src.modules.scene.generator import RuleBasedSceneGenerator, OllamaSceneGenerator
from src.modules.image.generator import DummyImageGenerator
from src.modules.tts.engine import DummyTTSEngine
from src.modules.animation.animator import FFmpegAnimator
from src.modules.video.composer import FFmpegComposer
from src.modules.video.subtitles import SubtitleGenerator
from src.modules.storage.local import LocalStorage


def main():
    parser = argparse.ArgumentParser(description="AI Cartoon Video Generator")
    parser.add_argument("--story", type=str, help="Story text or path to .txt file")
    parser.add_argument("--idea", type=str, help="Brief idea (LLM generates full story)")
    parser.add_argument("--type", type=str, default="cartoon",
                       choices=["cartoon", "motivation", "funny", "horror", "educational"],
                       help="Content type for story generation")
    parser.add_argument("--style", type=str, default="cartoon",
                       choices=["cartoon", "anime", "pixar", "comic"])
    parser.add_argument("--use-gpu", action="store_true")
    parser.add_argument("--use-llm", action="store_true", help="Use Ollama for scene splitting")
    parser.add_argument("--tts", type=str, default="dummy", choices=["piper", "coqui", "dummy"])
    parser.add_argument("--no-subtitles", action="store_true")
    args = parser.parse_args()

    # Load story from file or direct text
    story = ""
    if args.story:
        if Path(args.story).exists():
            story = Path(args.story).read_text(encoding="utf-8")
        else:
            story = args.story

    if not story and not args.idea:
        print("Provide --story or --idea")
        sys.exit(1)

    config = Config()
    config.ensure_dirs()

    # Build modules
    scene_gen = OllamaSceneGenerator() if args.use_llm else RuleBasedSceneGenerator()

    if args.use_gpu:
        from src.modules.image.generator import StableDiffusionGenerator
        image_gen = StableDiffusionGenerator(config)
    else:
        image_gen = DummyImageGenerator(config)

    if args.tts == "piper":
        from src.modules.tts.engine import PiperTTSEngine
        tts_engine = PiperTTSEngine(config)
    elif args.tts == "coqui":
        from src.modules.tts.engine import CoquiTTSEngine
        tts_engine = CoquiTTSEngine(config)
    else:
        tts_engine = DummyTTSEngine(config)

    story_gen = StoryGenerator() if args.idea else None
    subtitle_gen = None if args.no_subtitles else SubtitleGenerator()

    pipeline = Pipeline(
        scene_gen, image_gen, tts_engine,
        FFmpegAnimator(config), FFmpegComposer(config), LocalStorage(config),
        story_gen=story_gen, subtitle_gen=subtitle_gen
    )

    job = Job(story=story, idea=args.idea or "", style=args.style,
              content_type=args.type, subtitles=not args.no_subtitles)

    print(f"[*] Starting video generation [Job: {job.id}]")
    print(f"    Content Type: {args.type} | Style: {args.style}")
    if args.idea:
        print(f"    Idea: {args.idea}")
    else:
        print(f"    Story: {len(story)} chars")

    result = pipeline.run(job)

    if result.status.value == "completed":
        print(f"\n[DONE] Video generated: {result.output_path}")
        print(f"       Scenes: {len(result.scenes)}")
    else:
        print(f"\n[FAIL] {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
