from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.assessment.infrastructure.adapters.azure_speech import (  # noqa: E402
    AzureSpeechPronunciationAssessmentService,
)
from app.core.config import Settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a sanitized Azure Speech Pronunciation Assessment diagnostic."
    )
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--expected-text", required=True)
    parser.add_argument("--locale", default=None, help="Defaults to assessment configuration/es-MX")
    parser.add_argument(
        "--compare-locales",
        action="store_true",
        help="Run the same audio with es-MX and es-ES",
    )
    parser.add_argument(
        "--locales",
        nargs="+",
        help="Run an explicit list of locales (overrides --locale)",
    )
    parser.add_argument("--output-json", type=Path)
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include Azure detailed JSON (never includes credentials)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.audio.is_file():
        print(f"ERROR: audio file not found: {args.audio}", file=sys.stderr)
        return 2
    try:
        audio_content = args.audio.read_bytes()
    except OSError as exc:
        print(f"ERROR: could not read audio: {exc}", file=sys.stderr)
        return 2

    settings = Settings()
    service = AzureSpeechPronunciationAssessmentService(settings)
    locales = (
        args.locales
        or (["es-MX", "es-ES"] if args.compare_locales else [args.locale])
    )
    content_type = mimetypes.guess_type(args.audio.name)[0] or args.audio.suffix
    report = {
        "audio": str(args.audio),
        "expected_text": args.expected_text,
        "results": {},
    }
    failed = False
    for locale in locales:
        result = service.assess_pronunciation(
            audio_content=audio_content,
            reference_text=args.expected_text,
            language_code=locale,
            audio_format=content_type,
        )
        report["results"][result.language_code or locale or "default"] = result.to_dict(
            include_raw=args.include_raw
        )
        failed = failed or result.status != "completed"

    serialized = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    print(serialized)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(serialized + "\n", encoding="utf-8")
        print(f"Sanitized report written to {args.output_json}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
