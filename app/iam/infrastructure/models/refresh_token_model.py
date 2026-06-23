from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base import Base, UUIDPrimaryKeyMixin


class RefreshTokenModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "refresh_tokens_iam"

    user_id: Mapped[str] = mapped_column(
        Uuid, ForeignKey("users_iam.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("UserModel", back_populates="refresh_tokens")
