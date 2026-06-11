from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from sqlalchemy import String, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TeacherProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teacher_profiles"

    user_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    institution_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))

    user = relationship("User", back_populates="teacher_profile")
    classrooms = relationship("Classroom", back_populates="teacher_profile")
    sessions = relationship("AssessmentSession", back_populates="teacher_profile")
