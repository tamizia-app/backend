from app.iam.application.context.signin_context import SigninContext
from app.iam.application.context.signup_context import SignupContext
from app.iam.application.exceptions import ValidationException


class UserValidator:
    @staticmethod
    def validate_signup(context: SignupContext) -> None:
        errors: list[str] = []

        if not context.name or not context.name.strip():
            errors.append("Name is required.")

        if not context.lastname or not context.lastname.strip():
            errors.append("Lastname is required.")

        if not context.email or "@" not in context.email:
            errors.append("A valid email is required.")

        if not context.password or len(context.password) < 8:
            errors.append("Password must be at least 8 characters.")

        if errors:
            raise ValidationException("; ".join(errors))

    @staticmethod
    def validate_signin(context: SigninContext) -> None:
        errors: list[str] = []

        if not context.email or "@" not in context.email:
            errors.append("A valid email is required.")

        if not context.password:
            errors.append("Password is required.")

        if errors:
            raise ValidationException("; ".join(errors))
