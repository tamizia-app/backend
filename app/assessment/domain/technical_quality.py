from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.assessment.domain.enums import TechnicalStatus


SCORING_VERSION_PHASE2_V1 = "phase2_v1"

READING_PHASE2_COMPONENT_WEIGHTS = {
    "accuracy_score": 0.25,
    "fluency_score": 0.25,
    "pronunciation_score": 0.20,
    "completeness_score": 0.15,
    "lexical_match": 0.15,
}


PERFORMANCE_REASONS = frozenset(
    {
        "HIGH_WORD_ERROR_RATE",
        "HIGH_CHARACTER_ERROR_RATE",
        "LOW_ACCURACY_SCORE",
        "LOW_PRONUNCIATION_SCORE",
        "LOW_COMPLETENESS_SCORE",
        "LOW_TEXT_SIMILARITY",
        "LOW_LEXICAL_MATCH",
        "LOW_WORD_ACCURACY",
        "LOW_CHAR_ACCURACY",
        "EXTRA_WORDS_DETECTED",
        "OMITTED_WORDS_DETECTED",
    }
)


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
    fluency_score: float | None,
    completeness_score: float | None,
    lexical_match: float | None,
) -> tuple[float | None, dict[str, Any]]:
    named = {
        "accuracy_score": accuracy_score,
        "fluency_score": fluency_score,
        "pronunciation_score": pronunciation_score,
        "completeness_score": completeness_score,
        "lexical_match": lexical_match,
    }
    used = {name: value for name, value in named.items() if value is not None}
    available_weight_sum = sum(READING_PHASE2_COMPONENT_WEIGHTS[name] for name in used)
    score = (
        sum(value * READING_PHASE2_COMPONENT_WEIGHTS[name] for name, value in used.items())
        / available_weight_sum
        if available_weight_sum
        else None
    )
    if score is not None:
        score = max(0.0, min(100.0, score))
    included_components = list(used)
    excluded_components = [name for name, value in named.items() if value is None]
    return score, {
        **named,
        "formula_version": SCORING_VERSION_PHASE2_V1,
        "formula": "0.25_accuracy + 0.25_fluency + 0.20_pronunciation + 0.15_completeness + 0.15_lexical_match",
        "component_weights": READING_PHASE2_COMPONENT_WEIGHTS,
        "available_weight_sum": round(available_weight_sum, 4),
        "normalized": True,
        "included_components": included_components,
        "excluded_components": excluded_components,
        "used_components": list(used),
        "component_count": len(used),
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
        score_eligible=technical_status in (TechnicalStatus.VALID, TechnicalStatus.PARTIAL) and score is not None,
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

    if not (recognized_text or "").strip() or score is None:
        technical_status = TechnicalStatus.INVALID
    elif error_code or (confidence_avg is not None and confidence_avg < 0.70):
        technical_status = TechnicalStatus.PARTIAL
    else:
        technical_status = TechnicalStatus.VALID
    return TechnicalQuality(
        technical_status=technical_status,
        score_eligible=technical_status in (TechnicalStatus.VALID, TechnicalStatus.PARTIAL) and score is not None,
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
