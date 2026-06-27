from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base import Base, UUIDPrimaryKeyMixin

import uuid

class OSQuestionModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_os_questions"

    exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_exercises.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    question_text: Mapped[str] = mapped_column(String(500), nullable=False)
    image_blob_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class OSAnswerModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_os_answers"

    os_question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_os_questions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    correct_word: Mapped[str] = mapped_column(String(255), nullable=False)
    syllables_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class MCQuestionModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_mc_questions"

    exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_exercises.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    question_text: Mapped[str] = mapped_column(String(500), nullable=False)
    image_blob_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class MCAnswerOptionModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_mc_answer_options"

    mc_question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_mc_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(255), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
