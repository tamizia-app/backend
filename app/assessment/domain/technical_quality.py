from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.assessment.domain.enums import TechnicalStatus


READING_TECHNICAL_REASONS = frozenset(
    {
        "STT_PROVIDER_FAILED",
        "PRONUNCIATION_PROVIDER_FAILED",
        "EMPTY_ASR_TRANSCRIPTION",
        "HIGH_NO_SPEECH_PROBABILITY",
        "LOW_ASR_QUALITY",
        "LOW_WORD_PROBABILITY",
        "AUDIO_TOO_SHORT",
        "AUDIO_SEGMENT_DURATION_MISMATCH",
        "INVALID_WORD_TIMESTAMPS",
        "ASR_REPETITION",
        "ASR_AZURE_TRANSCRIPT_DIVERGENCE",
        "PARTIAL_EVALUATION",
        "FAILED_EVALUATION",
        "INVALID_AUDIO",
    }
)


@dataclass(frozen=True)
class TechnicalQuality:
    technical_status: TechnicalStatus
    score_eligible: bool
    manual_review_required: bool
    quality_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "technical_status": self.technical_status.value,
            "score_eligible": self.score_eligible,
            "manual_review_required": self.manual_review_required,
            "quality_reasons": self.quality_reasons,
        }


def calculate_reading_score(
    *,
    pronunciation_score: float | None,
    accuracy_score: float | None,
    completeness_score: float | None,
    lexical_match: float | None,
) -> tuple[float | None, dict[str, Any]]:
    named = {
        "pronunciation_score": pronunciation_score,
        "accuracy_score": accuracy_score,
        "completeness_score": completeness_score,
        "lexical_match": lexical_match,
    }
    used = {name: value for name, value in named.items() if value is not None}
    score = sum(used.values()) / len(used) if used else None
    return score, {
        **named,
        "used_components": list(used),
        "component_count": len(used),
        "formula": "arithmetic_mean_available_P_A_C_lexical",
    }


def reading_quality(pipeline_result: dict, score: float | None) -> TechnicalQuality:
    review = pipeline_result.get("review") or {}
    reasons = list(review.get("reasons") or [])
    status = str(pipeline_result.get("status") or "failed").lower()
    if status == "partial":
        reasons.append("PARTIAL_EVALUATION")
    elif status == "failed":
        reasons.append("FAILED_EVALUATION")
    reasons = _unique(reasons)

    if status == "failed" or score is None:
        technical_status = TechnicalStatus.INVALID
    elif status == "partial" or any(reason in READING_TECHNICAL_REASONS for reason in reasons):
        technical_status = TechnicalStatus.PARTIAL
    else:
        technical_status = TechnicalStatus.VALID
    return TechnicalQuality(
        technical_status=technical_status,
        score_eligible=technical_status == TechnicalStatus.VALID and score is not None,
        manual_review_required=bool(review.get("required")) or bool(reasons),
        quality_reasons=reasons,
    )


def invalid_reading_quality(reason: str) -> TechnicalQuality:
    return TechnicalQuality(
        technical_status=TechnicalStatus.INVALID,
        score_eligible=False,
        manual_review_required=True,
        quality_reasons=[reason],
    )


def writing_quality(
    *,
    recognized_text: str | None,
    confidence_avg: float | None,
    score: float | None,
    review_required: bool,
    review_reasons: list[str],
    error_code: str | None = None,
) -> TechnicalQuality:
    reasons = list(review_reasons)
    if error_code:
        reasons.append(f"OCR_PROVIDER_ERROR:{error_code}")
    if not (recognized_text or "").strip():
        reasons.append("EMPTY_RECOGNIZED_TEXT")
    reasons = _unique(reasons)

    if error_code or not (recognized_text or "").strip() or score is None:
        technical_status = TechnicalStatus.INVALID
    elif confidence_avg is not None and confidence_avg < 0.70:
        technical_status = TechnicalStatus.PARTIAL
    else:
        technical_status = TechnicalStatus.VALID
    return TechnicalQuality(
        technical_status=technical_status,
        score_eligible=technical_status == TechnicalStatus.VALID and score is not None,
        manual_review_required=review_required or bool(reasons),
        quality_reasons=reasons,
    )


def valid_discrete_quality(score: float | None) -> TechnicalQuality:
    valid = score is not None
    return TechnicalQuality(
        technical_status=TechnicalStatus.VALID if valid else TechnicalStatus.INVALID,
        score_eligible=valid,
        manual_review_required=not valid,
        quality_reasons=[] if valid else ["RESPONSE_NOT_SCORABLE"],
    )


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
