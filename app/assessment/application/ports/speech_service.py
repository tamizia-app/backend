from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class SpeechAssessmentResult:
    recognized_text: str | None = None
    pronunciation_score: float | None = None
    accuracy_score: float | None = None
    fluency_score: float | None = None
    completeness_score: float | None = None
    prosody_score: float | None = None
    raw_result_json: dict = field(default_factory=dict)
    language_code: str | None = None
    duration_ms: int | None = None
    error_message: str | None = None


class SpeechPronunciationAssessmentService(Protocol):
    def assess_pronunciation(
        self,
        audio_content: bytes,
        reference_text: str,
        language_code: str = "es-PE",
        audio_format: str | None = None,
    ) -> SpeechAssessmentResult: ...
