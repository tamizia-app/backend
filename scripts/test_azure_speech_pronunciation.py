"""
Manual SPIKE script for Azure Speech Pronunciation Assessment.

Usage:
    py scripts/test_azure_speech_pronunciation.py --audio path/to/audio.wav --text "mi texto de referencia"

Options:
    --audio         Path to a WAV audio file
    --text          Reference text for pronunciation assessment
    --language      Language code (default: es-PE)
    --region        Azure region (default: centralus)
    --key           Azure Speech key (optional, reads env var AZURE_SPEECH_KEY)
    --endpoint      Custom endpoint (optional)
    --outdir        Output directory (default: local_storage/debug)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assessment.infrastructure.adapters.azure_speech import (
    AzureSpeechPronunciationAssessmentService,
)
from app.core.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Azure Speech Pronunciation Assessment")
    parser.add_argument("--audio", required=True, help="Path to WAV audio file")
    parser.add_argument("--text", required=True, help="Reference text")
    parser.add_argument("--language", default="es-PE", help="Language code")
    parser.add_argument("--region", default="centralus", help="Azure region")
    parser.add_argument("--key", default=None, help="Azure Speech key (or AZURE_SPEECH_KEY env)")
    parser.add_argument("--endpoint", default=None, help="Custom endpoint")
    parser.add_argument("--outdir", default="local_storage/debug", help="Output directory")

    args = parser.parse_args()

    # Load from .env first, then override with CLI args
    base_settings = Settings()
    speech_key = args.key or base_settings.azure_speech_key or os.getenv("AZURE_SPEECH_KEY")
    if not speech_key:
        print("ERROR: AZURE_SPEECH_KEY not set. Provide --key, set AZURE_SPEECH_KEY in .env, or set env var.")
        sys.exit(1)

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"ERROR: Audio file not found: {audio_path}")
        sys.exit(1)

    settings = Settings(
        _env_file=None,
        azure_speech_key=speech_key,
        azure_speech_region=args.region or base_settings.azure_speech_region or "centralus",
        azure_speech_endpoint=args.endpoint or base_settings.azure_speech_endpoint,
    )

    service = AzureSpeechPronunciationAssessmentService(settings)

    audio_bytes = audio_path.read_bytes()
    print(f"Assessing pronunciation...")
    print(f"  Language: {args.language}")
    print(f"  Reference text: {args.text}")
    print(f"  Audio: {audio_path} ({len(audio_bytes)} bytes)")
    print(f"  Region: {args.region}")
    print(f"  Endpoint: {args.endpoint or '(not set)'}")
    print()

    result = service.assess_pronunciation(
        audio_content=audio_bytes,
        reference_text=args.text,
        language_code=args.language,
    )

    print("=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"  recognized_text:   {result.recognized_text}")
    print(f"  pronunciation_score: {result.pronunciation_score}")
    print(f"  accuracy_score:    {result.accuracy_score}")
    print(f"  fluency_score:     {result.fluency_score}")
    print(f"  completeness_score: {result.completeness_score}")
    print(f"  prosody_score:     {result.prosody_score}")
    print(f"  duration_ms:       {result.duration_ms}")
    print(f"  error_message:     {result.error_message}")
    print()

    # Save raw JSON
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / f"speech_result_{args.language}.json"
    report = {
        "input": {
            "audio": str(audio_path),
            "reference_text": args.text,
            "language": args.language,
            "region": args.region,
            "endpoint": args.endpoint,
        },
        "result": {
            "recognized_text": result.recognized_text,
            "pronunciation_score": result.pronunciation_score,
            "accuracy_score": result.accuracy_score,
            "fluency_score": result.fluency_score,
            "completeness_score": result.completeness_score,
            "prosody_score": result.prosody_score,
            "duration_ms": result.duration_ms,
            "error_message": result.error_message,
            "raw_result_json": result.raw_result_json,
        },
    }
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Full result saved to: {out_path}")


if __name__ == "__main__":
    main()
