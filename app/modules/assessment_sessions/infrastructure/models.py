from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import SessionStatus
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AssessmentSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_sessions"

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    teacher_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        default=SessionStatus.PENDING,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    student = relationship("Student", back_populates="sessions")
    exercise = relationship("Exercise", back_populates="sessions")
    teacher_profile = relationship("TeacherProfile", back_populates="sessions")
    writing_sample = relationship("WritingSample", back_populates="session", uselist=False)
    audio_sample = relationship("AudioSample", back_populates="session", uselist=False)
    result = relationship("SessionResult", back_populates="session", uselist=False)

