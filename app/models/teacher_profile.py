from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TeacherProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teacher_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    institution_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))

    user = relationship("User", back_populates="teacher_profile")
    classrooms = relationship("Classroom", back_populates="teacher_profile")
    sessions = relationship("AssessmentSession", back_populates="teacher_profile")
