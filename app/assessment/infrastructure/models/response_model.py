from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base import Base, UUIDPrimaryKeyMixin

import uuid

class MCResponseModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_mc_responses"

    exercise_attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_exercise_attempts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    selected_option_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_mc_answer_options.id", ondelete="CASCADE"), nullable=False
    )
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class OSResponseModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_os_responses"

    exercise_attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_exercise_attempts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    selected_syllables_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    formed_word: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class SpeakingResponseModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_speaking_responses"

    exercise_attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_exercise_attempts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    audio_blob_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recognized_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    free_transcription_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    assessment_recognized_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


class WritingResponseModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_writing_responses"

    exercise_attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_exercise_attempts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    image_blob_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recognized_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
