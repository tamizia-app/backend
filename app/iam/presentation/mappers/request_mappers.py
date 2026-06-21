from app.iam.application.context.forgot_password_context import ForgotPasswordContext
from app.iam.application.context.refresh_context import RefreshContext
from app.iam.application.context.reset_password_context import ResetPasswordContext
from app.iam.application.context.signin_context import SigninContext
from app.iam.application.context.signout_context import SignoutContext
from app.iam.application.context.signup_context import SignupContext
from app.iam.presentation.schemas import (
    ForgotPasswordRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SigninRequest,
    SignoutRequest,
    SignupRequest,
)


class RequestMapper:
    @staticmethod
    def to_signup_context(request: SignupRequest) -> SignupContext:
        return SignupContext(
            name=request.name,
            lastname=request.lastname,
            email=request.email,
            password=request.password,
        )

    @staticmethod
    def to_signin_context(request: SigninRequest) -> SigninContext:
        return SigninContext(
            email=request.email,
            password=request.password,
        )

    @staticmethod
    def to_refresh_context(request: RefreshRequest) -> RefreshContext:
        return RefreshContext(refresh_token=request.refresh_token)

    @staticmethod
    def to_signout_context(request: SignoutRequest) -> SignoutContext:
        return SignoutContext(refresh_token=request.refresh_token)

    @staticmethod
    def to_forgot_password_context(request: ForgotPasswordRequest) -> ForgotPasswordContext:
        return ForgotPasswordContext(email=request.email)

    @staticmethod
    def to_reset_password_context(request: ResetPasswordRequest) -> ResetPasswordContext:
        return ResetPasswordContext(token=request.token, new_password=request.new_password)
