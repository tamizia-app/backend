from app.iam.domain.password_reset import PasswordResetToken
from app.iam.domain.refresh_token import RefreshToken
from app.iam.domain.user import User
from app.iam.infrastructure.models.password_reset_token_model import PasswordResetTokenModel
from app.iam.infrastructure.models.refresh_token_model import RefreshTokenModel
from app.iam.infrastructure.models.user_model import UserModel


class ModelMapper:
    @staticmethod
    def user_to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            name=model.name,
            lastname=model.lastname,
            email=model.email,
            password_hash=model.password_hash,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def refresh_token_to_domain(model: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            created_at=model.created_at,
            revoked_at=model.revoked_at,
        )

    @staticmethod
    def password_reset_token_to_domain(model: PasswordResetTokenModel) -> PasswordResetToken:
        return PasswordResetToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            used_at=model.used_at,
            created_at=model.created_at,
        )
