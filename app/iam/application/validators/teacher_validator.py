from app.iam.application.context.signup_context import SignupContext
from app.iam.application.exceptions import ValidationException


class TeacherValidator:
    @staticmethod
    def validate_signup(context: SignupContext) -> None:
        errors: list[str] = []

        if context.phone and not context.phone.strip():
            errors.append("Phone must not be empty if provided.")

        if context.institute_name and not context.institute_name.strip():
            errors.append("Institute name must not be empty if provided.")

        if errors:
            raise ValidationException("; ".join(errors))
