from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.iam.application.commands.create_refresh_token import CreateRefreshTokenCommand
from app.iam.application.ports.repositories import (
    RefreshTokenRepository as RefreshTokenRepositoryPort,
)
from app.iam.domain.refresh_token import RefreshToken
from app.iam.infrastructure.mappers.model_mappers import ModelMapper
from app.iam.infrastructure.models.refresh_token_model import RefreshTokenModel


class SQLAlchemyRefreshTokenRepository(RefreshTokenRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        model = self._db.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        return ModelMapper.refresh_token_to_domain(model) if model else None

    def create(self, command: CreateRefreshTokenCommand) -> RefreshToken:
        model = RefreshTokenModel(
            user_id=command.user_id,
            token_hash=command.token_hash,
        )
        self._db.add(model)
        self._db.flush()
        return ModelMapper.refresh_token_to_domain(model)

    def revoke(self, token_id: UUID) -> None:
        model = self._db.get(RefreshTokenModel, token_id)
        if model and model.revoked_at is None:
            model.revoked_at = datetime.now(UTC)
            self._db.flush()
