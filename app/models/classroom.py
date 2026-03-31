from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Classroom(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "classrooms"

    teacher_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teacher_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    grade_level: Mapped[str] = mapped_column(String(50), nullable=False)
    section: Mapped[str | None] = mapped_column(String(50))
    school_year: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    teacher_profile = relationship("TeacherProfile", back_populates="classrooms")
    students = relationship("Student", back_populates="classroom")
