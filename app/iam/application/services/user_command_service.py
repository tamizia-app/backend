from datetime import timedelta
from uuid import UUID

from app.iam.application.commands.create_refresh_token import (
    CreateRefreshTokenCommand,
)
from app.iam.application.commands.create_user import CreateUserCommand
from app.iam.application.context.refresh_context import RefreshContext
from app.iam.application.context.signin_context import SigninContext
from app.iam.application.context.signout_context import SignoutContext
from app.iam.application.context.signup_context import SignupContext
from app.iam.application.exceptions import (
    InactiveUserException,
    InvalidCredentialsException,
)
from app.iam.application.ports.repositories import (
    RefreshTokenRepository,
    UserRepository,
)
from app.iam.application.validators.user_validator import UserValidator
from app.core.config import Settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


class UserCommandServiceImpl:
    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo

    def ensure_user(self, context: SignupContext) -> UUID:
        UserValidator.validate_signup(context)

        existing = self._user_repo.find_by_email(context.email)
        if existing:
            return existing.id

        user = self._user_repo.create(
            CreateUserCommand(
                name=context.name,
                lastname=context.lastname,
                email=context.email,
                password_hash=hash_password(context.password),
            )
        )
        return user.id

    def signin(
        self,
        context: SigninContext,
        settings: Settings,
    ) -> tuple[str, str, int]:
        UserValidator.validate_signin(context)

        user = self._user_repo.find_by_email(context.email)
        if not user or not verify_password(context.password, user.password_hash):
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InactiveUserException()

        expires_in = int(timedelta(hours=8).total_seconds())
        access_token = create_access_token(
            subject=str(user.id),
            settings=settings,
            expires_delta=timedelta(hours=8),
        )

        raw_refresh_token = generate_refresh_token()
        token_hash = hash_refresh_token(raw_refresh_token, settings)
        self._refresh_token_repo.create(
            CreateRefreshTokenCommand(
                user_id=user.id,
                token_hash=token_hash,
            )
        )

        return access_token, raw_refresh_token, expires_in

    def refresh(
        self,
        context: RefreshContext,
        settings: Settings,
    ) -> tuple[str, str, int]:
        token_hash = hash_refresh_token(context.refresh_token, settings)
        stored = self._refresh_token_repo.find_by_hash(token_hash)

        if not stored or stored.revoked_at is not None:
            raise InvalidCredentialsException("Invalid refresh token.")

        user = self._user_repo.find_by_id(stored.user_id)
        if not user or not user.is_active:
            raise InactiveUserException()

        self._refresh_token_repo.revoke(stored.id)

        expires_in = int(timedelta(hours=8).total_seconds())
        access_token = create_access_token(
            subject=str(user.id),
            settings=settings,
            expires_delta=timedelta(hours=8),
        )

        raw_refresh_token = generate_refresh_token()
        new_hash = hash_refresh_token(raw_refresh_token, settings)
        self._refresh_token_repo.create(
            CreateRefreshTokenCommand(
                user_id=user.id,
                token_hash=new_hash,
            )
        )

        return access_token, raw_refresh_token, expires_in

    def signout(
        self,
        context: SignoutContext,
        settings: Settings,
    ) -> None:
        token_hash = hash_refresh_token(context.refresh_token, settings)
        stored = self._refresh_token_repo.find_by_hash(token_hash)
        if stored and stored.revoked_at is None:
            self._refresh_token_repo.revoke(stored.id)
