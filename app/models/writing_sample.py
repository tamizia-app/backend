from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class WritingSample(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "writing_samples"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessment_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    stroke_count: Mapped[int | None] = mapped_column(Integer)
    correction_count: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    session = relationship("AssessmentSession", back_populates="writing_sample")
    analysis = relationship("OCRAnalysis", back_populates="writing_sample", uselist=False)
