from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.iam.application.commands.create_user import CreateUserCommand
from app.iam.application.ports.repositories import UserRepository as UserRepositoryPort
from app.iam.domain.user import User
from app.iam.infrastructure.mappers.model_mappers import ModelMapper
from app.iam.infrastructure.models.user_model import UserModel


class SQLAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_email(self, email: str) -> User | None:
        model = self._db.scalar(select(UserModel).where(UserModel.email == email))
        return ModelMapper.user_to_domain(model) if model else None

    def find_by_id(self, user_id: UUID) -> User | None:
        model = self._db.scalar(select(UserModel).where(UserModel.id == user_id))
        return ModelMapper.user_to_domain(model) if model else None

    def create(self, command: CreateUserCommand) -> User:
        model = UserModel(
            name=command.name,
            lastname=command.lastname,
            email=command.email,
            password_hash=command.password_hash,
        )
        self._db.add(model)
        self._db.flush()
        return ModelMapper.user_to_domain(model)

    def exists_by_email(self, email: str) -> bool:
        return self._db.scalar(select(UserModel.id).where(UserModel.email == email)) is not None
