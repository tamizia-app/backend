from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.assessment.domain.enums import InterventionLevel


@dataclass
class SpeakingMetrics:
    id: UUID
    speaking_response_id: UUID
    pronunciation_score: float | None
    accuracy_score: float | None
    fluency_score: float | None
    completeness_score: float | None
    prosody_score: float | None
    raw_speech_result_json: dict | None
    created_at: datetime
    updated_at: datetime
    raw_transcription_result_json: dict | None = None


@dataclass
class WritingMetrics:
    id: UUID
    writing_response_id: UUID
    created_at: datetime
    updated_at: datetime
    confidence_avg: float | None = None
    cer: float | None = None
    wer: float | None = None
    similarity_score: float | None = None
    raw_ocr_result_json: dict | None = None
    duration_ms: int | None = None
    stroke_count: int | None = None
    point_count: int | None = None
    average_speed: float | None = None
    speed_variability: float | None = None
    pause_count: int | None = None
    longest_pause_ms: int | None = None
    total_pause_time_ms: int | None = None
    pressure_min: float | None = None
    pressure_max: float | None = None
    pressure_avg: float | None = None
    bounding_box_json: dict | None = None
    writing_area_usage: float | None = None


@dataclass
class AssessmentResult:
    id: UUID
    assessment_attempt_id: UUID
    final_score: float | None
    max_score: float | None
    mc_correct_count: int | None
    os_correct_count: int | None
    speaking_completed_count: int | None
    writing_completed_count: int | None
    intervention_level: InterventionLevel | None
    generated_at: datetime
    created_at: datetime
    updated_at: datetime
    speaking_average_score: float | None = None
    speaking_review_required_count: int = 0
    total_exercises: int = 0
    evaluated_exercises: int = 0
    pending_exercises: int = 0
    writing_average_score: float | None = None
    writing_review_required_count: int = 0
