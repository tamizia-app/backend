from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.assessment.application.use_cases.assess_reading_pipeline import (  # noqa: E402
    AssessReadingCommand,
    AssessReadingPipelineUseCase,
)
from app.assessment.infrastructure.adapters.azure_speech import (  # noqa: E402
    AzureSpeechPronunciationAssessmentService,
)
from app.assessment.infrastructure.adapters.faster_whisper_stt import (  # noqa: E402
    FasterWhisperSpeechToTextAdapter,
    WhisperConfig,
)
from app.assessment.infrastructure.audio_processing import (  # noqa: E402
    AssessmentAudioProcessor,
    AudioProcessingError,
)
from app.core.config import Settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose the independent Whisper + Azure reading pipeline."
    )
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--expected-text", required=True)
    parser.add_argument("--locale", default=None, help="Azure assessment locale")
    parser.add_argument(
        "--whisper-model",
        choices=("tiny", "base", "small"),
        help="Override WHISPER_MODEL_SIZE for this diagnostic",
    )
    parser.add_argument("--skip-azure", action="store_true")
    parser.add_argument("--output-json", type=Path)
    return parser.parse_args()


async def run(args: argparse.Namespace) -> dict:
    if not args.audio.is_file():
        raise ValueError(f"Audio file not found: {args.audio}")
    config = WhisperConfig.from_environment()
    if args.whisper_model:
        config = replace(config, model_size=args.whisper_model)
    use_case = AssessReadingPipelineUseCase(
        audio_processor=AssessmentAudioProcessor(),
        stt_service=FasterWhisperSpeechToTextAdapter(config),
        pronunciation_service=AzureSpeechPronunciationAssessmentService(Settings()),
        low_logprob_threshold=config.low_confidence_threshold,
    )
    return await use_case.execute(
        AssessReadingCommand(
            audio_content=args.audio.read_bytes(),
            expected_text=args.expected_text,
            audio_format=mimetypes.guess_type(args.audio.name)[0] or args.audio.suffix,
            assessment_locale=args.locale,
            skip_azure=args.skip_azure,
        )
    )


def main() -> int:
    args = parse_args()
    try:
        result = asyncio.run(run(args))
    except (AudioProcessingError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    serialized = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    print(serialized)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(serialized + "\n", encoding="utf-8")
        print(f"Sanitized report written to {args.output_json}", file=sys.stderr)
    return 0 if result["status"] in {"completed", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
