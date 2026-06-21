from abc import ABC, abstractmethod
from uuid import UUID

from app.iam.application.commands.create_password_reset_token import (
    CreatePasswordResetTokenCommand,
)
from app.iam.application.commands.create_refresh_token import CreateRefreshTokenCommand
from app.iam.application.commands.create_user import CreateUserCommand
from app.iam.domain.password_reset import PasswordResetToken
from app.iam.domain.refresh_token import RefreshToken
from app.iam.domain.user import User


class UserRepository(ABC):
    @abstractmethod
    def find_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def find_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    def create(self, command: CreateUserCommand) -> User: ...

    @abstractmethod
    def exists_by_email(self, email: str) -> bool: ...

    @abstractmethod
    def update(self, user_id: UUID, name: str, lastname: str, email: str) -> User | None: ...

    @abstractmethod
    def update_password(self, user_id: UUID, new_password_hash: str) -> None: ...


class RefreshTokenRepository(ABC):
    @abstractmethod
    def find_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    @abstractmethod
    def create(self, command: CreateRefreshTokenCommand) -> RefreshToken: ...

    @abstractmethod
    def revoke(self, token_id: UUID) -> None: ...


class PasswordResetTokenRepository(ABC):
    @abstractmethod
    def create(self, command: CreatePasswordResetTokenCommand) -> PasswordResetToken: ...

    @abstractmethod
    def find_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None: ...

    @abstractmethod
    def mark_used(self, token_id: UUID) -> None: ...
