from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base import Base, UUIDPrimaryKeyMixin

import uuid

class PromptExerciseModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_prompt_exercises"

    exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_exercises.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    prompt_text: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    text_to_show: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_blob_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_blob_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language_code: Mapped[str] = mapped_column(String(20), nullable=False, default="es-PE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class ExpectedAnswerModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_expected_answers"

    prompt_exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_prompt_exercises.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    expected_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
