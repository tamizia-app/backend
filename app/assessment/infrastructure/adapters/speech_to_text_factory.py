from __future__ import annotations

from typing import Any

from app.assessment.application.ports.speech_to_text import SpeechToTextPort
from app.assessment.infrastructure.adapters.crisper_whisper_stt import (
    CrisperWhisperConfig,
    CrisperWhisperSpeechToTextAdapter,
)
from app.assessment.infrastructure.adapters.faster_whisper_stt import (
    FasterWhisperSpeechToTextAdapter,
    WhisperConfig,
)


def build_speech_to_text_service(settings: Any) -> tuple[SpeechToTextPort, float]:
    if settings.assessment_stt_provider == "crisper_whisper":
        config = CrisperWhisperConfig.from_settings(settings)
        return (
            CrisperWhisperSpeechToTextAdapter(config),
            config.low_confidence_threshold,
        )

    config = WhisperConfig.from_settings(settings)
    return (
        FasterWhisperSpeechToTextAdapter(config),
        config.low_confidence_threshold,
    )
