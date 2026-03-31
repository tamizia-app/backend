from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class AudioSample(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audio_samples"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessment_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    audio_url: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    locale: Mapped[str] = mapped_column(String(20), default="es-CO", nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    session = relationship("AssessmentSession", back_populates="audio_sample")
    analysis = relationship("PronunciationAnalysis", back_populates="audio_sample", uselist=False)
