from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.assessment.domain.enums import InterventionLevel
from app.shared.base import Base, UUIDPrimaryKeyMixin

import uuid

class SpeakingMetricsModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_speaking_metrics"

    speaking_response_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_speaking_responses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    pronunciation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fluency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    prosody_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_speech_result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_transcription_result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    comparison_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    review_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quality_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    original_pronunciation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_pronunciation_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_fluency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_fluency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_lexical_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_lexical_match: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_prosody_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_prosody_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class WritingMetricsModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_writing_metrics"

    writing_response_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_writing_responses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    confidence_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    cer: Mapped[float | None] = mapped_column(Float, nullable=True)
    wer: Mapped[float | None] = mapped_column(Float, nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_ocr_result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stroke_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    point_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_variability: Mapped[float | None] = mapped_column(Float, nullable=True)
    pause_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    longest_pause_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_pause_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pressure_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounding_box_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    writing_area_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quality_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    original_char_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_char_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_word_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_word_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class AssessmentResultModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_results"

    assessment_attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mc_correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    os_correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speaking_completed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    writing_completed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intervention_level: Mapped[InterventionLevel | None] = mapped_column(String(20), nullable=True)
    speaking_average_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    speaking_review_required_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_exercises: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evaluated_exercises: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_exercises: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    writing_average_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    writing_review_required_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_denominator: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scoring_snapshot_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    original_final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_scoring_snapshot_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    current_scoring_snapshot_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class ExerciseScoreModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_exercise_scores"

    exercise_attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_exercise_attempts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    exercise_type: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    technical_status: Mapped[str] = mapped_column(String(20), nullable=False)
    manual_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_reasons_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    scoring_components_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    original_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_scoring_components_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    current_scoring_components_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    manual_adjustment_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_required")
    teacher_observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    adjusted_by_teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("teachers_iam.id", ondelete="SET NULL"), nullable=True
    )
    adjusted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
