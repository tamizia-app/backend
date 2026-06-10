from app.iam.domain.refresh_token import RefreshToken
from app.iam.domain.teacher import Teacher
from app.iam.domain.user import User
from app.iam.infrastructure.models.refresh_token_model import RefreshTokenModel
from app.iam.infrastructure.models.teacher_model import TeacherModel
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
    def teacher_to_domain(model: TeacherModel) -> Teacher:
        return Teacher(
            id=model.id,
            user_id=model.user_id,
            institute_name=model.institute_name,
            phone=model.phone,
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
