from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import RiskFlag
from app.models.base import Base, UUIDPrimaryKeyMixin


class SessionResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "session_results"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessment_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    writing_score: Mapped[float | None] = mapped_column(Float)
    reading_score: Mapped[float | None] = mapped_column(Float)
    overall_score: Mapped[float | None] = mapped_column(Float)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    risk_flag: Mapped[RiskFlag] = mapped_column(
        Enum(RiskFlag, values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    session = relationship("AssessmentSession", back_populates="result")

