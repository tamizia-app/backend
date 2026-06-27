from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.assessment.domain.enums import ExerciseType
from app.shared.base import Base, UUIDPrimaryKeyMixin

import uuid

class AssessmentExerciseModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_exercises"

    type: Mapped[ExerciseType] = mapped_column(
        String(50), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    stimulus_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    response_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    difficulty_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("teachers_iam.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
