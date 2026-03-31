from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class PronunciationAnalysis(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pronunciation_analyses"

    audio_sample_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("audio_samples.id", ondelete="CASCADE"), unique=True, nullable=False)
    accuracy_score: Mapped[float | None] = mapped_column(Float)
    fluency_score: Mapped[float | None] = mapped_column(Float)
    completeness_score: Mapped[float | None] = mapped_column(Float)
    pronunciation_score: Mapped[float | None] = mapped_column(Float)
    recognized_text: Mapped[str | None] = mapped_column(Text)
    raw_response: Mapped[dict | None] = mapped_column(JSON)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    audio_sample = relationship("AudioSample", back_populates="analysis")
