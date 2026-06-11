from app.iam.application.results.refresh_result import RefreshResult
from app.iam.application.results.signin_result import SigninResult
from app.iam.application.results.signout_result import SignoutResult
from app.iam.application.results.signup_result import SignupResult


class AuthAssembler:
    @staticmethod
    def to_signup_result(
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> SignupResult:
        return SignupResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
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
