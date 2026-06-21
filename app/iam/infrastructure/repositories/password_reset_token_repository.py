from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.iam.application.commands.create_password_reset_token import (
    CreatePasswordResetTokenCommand,
)
from app.iam.application.ports.repositories import (
    PasswordResetTokenRepository as PasswordResetTokenRepositoryPort,
)
from app.iam.domain.password_reset import PasswordResetToken
from app.iam.infrastructure.mappers.model_mappers import ModelMapper
from app.iam.infrastructure.models.password_reset_token_model import PasswordResetTokenModel


class SQLAlchemyPasswordResetTokenRepository(PasswordResetTokenRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, command: CreatePasswordResetTokenCommand) -> PasswordResetToken:
        model = PasswordResetTokenModel(
            user_id=command.user_id,
            token_hash=command.token_hash,
            expires_at=command.expires_at,
        )
        self._db.add(model)
        self._db.flush()
        return ModelMapper.password_reset_token_to_domain(model)

    def find_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        now = datetime.now(UTC)
        model = self._db.scalar(
            select(PasswordResetTokenModel).where(
                PasswordResetTokenModel.token_hash == token_hash,
                PasswordResetTokenModel.expires_at > now,
                PasswordResetTokenModel.used_at.is_(None),
            )
        )
        return ModelMapper.password_reset_token_to_domain(model) if model else None

    def mark_used(self, token_id: UUID) -> None:
        model = self._db.get(PasswordResetTokenModel, token_id)
        if model and model.used_at is None:
            model.used_at = datetime.now(UTC)
            self._db.flush()
