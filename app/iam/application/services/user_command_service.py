import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.email import send_email
from app.iam.application.commands.create_password_reset_token import (
    CreatePasswordResetTokenCommand,
)
from app.iam.application.commands.create_refresh_token import (
    CreateRefreshTokenCommand,
)
from app.iam.application.commands.create_user import CreateUserCommand
from app.iam.application.context.forgot_password_context import ForgotPasswordContext
from app.iam.application.context.refresh_context import RefreshContext
from app.iam.application.context.reset_password_context import ResetPasswordContext
from app.iam.application.context.signin_context import SigninContext
from app.iam.application.context.signout_context import SignoutContext
from app.iam.application.context.signup_context import SignupContext
from app.iam.application.exceptions import (
    AlreadyExistsException,
    InactiveUserException,
    InvalidCredentialsException,
    NotFoundException,
)
from app.iam.application.ports.repositories import (
    PasswordResetTokenRepository,
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
        password_reset_repo: PasswordResetTokenRepository | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._password_reset_repo = password_reset_repo

    def signup(self, context: SignupContext, settings: Settings) -> tuple[str, str, int]:
        UserValidator.validate_signup(context)

        if self._user_repo.exists_by_email(context.email):
            raise AlreadyExistsException("A user with this email already exists.")

        user = self._user_repo.create(
            CreateUserCommand(
                name=context.name,
                lastname=context.lastname,
                email=context.email,
                password_hash=hash_password(context.password),
            )
        )

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

    def forgot_password(self, context: ForgotPasswordContext, settings: Settings) -> None:
        user = self._user_repo.find_by_email(context.email)
        if not user:
            raise NotFoundException("No user found with this email.")

        raw_token = secrets.token_urlsafe(48)
        token_hash = hash_refresh_token(raw_token, settings)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.reset_token_expire_minutes)

        if self._password_reset_repo:
            self._password_reset_repo.create(
                CreatePasswordResetTokenCommand(
                    user_id=user.id,
                    token_hash=token_hash,
                    expires_at=expires_at,
                )
            )

        reset_link = f"{raw_token}"
        body = (
            f"Hello,\n\n"
            f"You requested a password reset. Use this token:\n\n{raw_token}\n\n"
            f"It expires in {settings.reset_token_expire_minutes} minutes.\n\n"
            f"If you did not request this, ignore this email."
        )
        send_email(to=user.email, subject="Password Reset", body=body, settings=settings)

    def reset_password(self, context: ResetPasswordContext, settings: Settings) -> None:
        if not context.new_password or len(context.new_password) < 8:
            raise InvalidCredentialsException("Password must be at least 8 characters.")

        token_hash = hash_refresh_token(context.token, settings)

        if not self._password_reset_repo:
            raise NotFoundException("Password reset not available.")

        stored = self._password_reset_repo.find_valid_by_hash(token_hash)
        if not stored:
            raise InvalidCredentialsException("Invalid or expired reset token.")

        new_hash = hash_password(context.new_password)
        self._user_repo.update_password(stored.user_id, new_hash)
        self._password_reset_repo.mark_used(stored.id)
