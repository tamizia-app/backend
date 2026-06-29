from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.assessment.domain.enums import AttemptStatus, ExerciseAttemptStatus
from app.shared.base import Base, UUIDPrimaryKeyMixin

import uuid

class AssessmentAttemptModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_attempts"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[AttemptStatus] = mapped_column(
        String(20), nullable=False, default=AttemptStatus.IN_PROGRESS
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    repeated_from_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("assessment_attempts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    repeat_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class ExerciseAttemptModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_exercise_attempts"

    assessment_attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_template_exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ExerciseAttemptStatus] = mapped_column(
        String(20), nullable=False, default=ExerciseAttemptStatus.PENDING
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
