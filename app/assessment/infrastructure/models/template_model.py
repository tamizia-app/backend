from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.assessment.domain.template import DEFAULT_TEMPLATE_EXERCISE_POINTS
from app.shared.base import Base, UUIDPrimaryKeyMixin

import uuid

class AssessmentTemplateModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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


class AssessmentTemplateExerciseModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_template_exercises"
    __table_args__ = (
        CheckConstraint("points IN (1, 2, 3)", name="ck_assessment_template_exercises_points_phase2"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=DEFAULT_TEMPLATE_EXERCISE_POINTS)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
