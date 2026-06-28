from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Uuid, func
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
