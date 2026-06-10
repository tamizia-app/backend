from app.iam.application.results.refresh_result import RefreshResult
from app.iam.application.results.signin_result import SigninResult
from app.iam.application.results.signout_result import SignoutResult
from app.iam.application.results.signup_result import SignupResult
from app.iam.domain.teacher import Teacher
from app.iam.domain.user import User


class AuthAssembler:
    @staticmethod
    def to_signup_result(user: User, teacher: Teacher) -> SignupResult:
        return SignupResult(
            user_id=user.id,
            teacher_id=teacher.id,
            name=user.name,
            lastname=user.lastname,
            email=user.email,
            institute_name=teacher.institute_name,
            phone=teacher.phone,
            created_at=teacher.created_at,
        )

    @staticmethod
    def to_signin_result(
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> SigninResult:
        return SigninResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    @staticmethod
    def to_refresh_result(
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> RefreshResult:
        return RefreshResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    @staticmethod
    def to_signout_result() -> SignoutResult:
        return SignoutResult(message="Logged out successfully.")
