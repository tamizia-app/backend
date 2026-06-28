from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class SpeechAssessmentResult:
    status: str = "error"
    expected_text: str | None = None
    recognized_text: str | None = None
    assessment_display_text: str | None = None
    assessment_lexical_text: str | None = None
    pronunciation_score: float | None = None
    accuracy_score: float | None = None
    fluency_score: float | None = None
    completeness_score: float | None = None
    prosody_score: float | None = None
    prosody_supported: bool = False
    words: list[dict] = field(default_factory=list)
    comparison: dict | None = None
    diagnostics: dict = field(default_factory=dict)
    raw_result_json: dict = field(default_factory=dict)
    language_code: str | None = None
    duration_ms: int | None = None
    error_message: str | None = None
    error_code: str | None = None

    def to_dict(self, *, include_raw: bool = False) -> dict:
        response = {
            "status": self.status,
            "expected_text": self.expected_text,
            "recognized_text": self.recognized_text,
            "assessment_display_text": self.assessment_display_text,
            "assessment_lexical_text": self.assessment_lexical_text,
            "locale": self.language_code,
            "pronunciation_assessment": {
                "accuracy_score": self.accuracy_score,
                "fluency_score": self.fluency_score,
                "completeness_score": self.completeness_score,
                "pronunciation_score": self.pronunciation_score,
                "prosody_score": self.prosody_score,
                "prosody_supported": self.prosody_supported,
                "words": self.words,
            },
            "comparison": self.comparison,
            "diagnostics": self.diagnostics,
            "error": (
                {"code": self.error_code, "message": self.error_message}
                if self.error_message
                else None
            ),
            # Compatibility with the original development endpoint.
            "language_code": self.language_code,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "pronunciation_score": self.pronunciation_score,
            "accuracy_score": self.accuracy_score,
            "fluency_score": self.fluency_score,
            "completeness_score": self.completeness_score,
            "prosody_score": self.prosody_score,
            "missing_fields": [
                name
                for name, value in {
                    "pronunciation_score": self.pronunciation_score,
                    "accuracy_score": self.accuracy_score,
                    "fluency_score": self.fluency_score,
                    "completeness_score": self.completeness_score,
                    "prosody_score": self.prosody_score,
                }.items()
                if value is None
            ],
        }
        if include_raw:
            response["raw_result_json"] = self.raw_result_json
        return response


class SpeechPronunciationAssessmentService(Protocol):
    def assess_pronunciation(
        self,
        audio_content: bytes,
        reference_text: str,
        language_code: str | None = None,
        audio_format: str | None = None,
    ) -> SpeechAssessmentResult: ...
