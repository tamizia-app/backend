from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.assessment.domain.enums import AssessmentStatus
from app.shared.base import Base, UUIDPrimaryKeyMixin

import uuid

class AssessmentModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessments"

    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("school_classrooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    homeroom_teacher_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("teachers_iam.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[AssessmentStatus] = mapped_column(String(20), nullable=False, default=AssessmentStatus.DRAFT)
    scheduled_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
