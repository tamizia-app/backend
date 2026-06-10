from app.iam.application.assemblers.auth_assembler import AuthAssembler
from app.iam.application.commands.signup import SignupCommand
from app.iam.application.context.signup_context import SignupContext
from app.iam.application.exceptions import AlreadyExistsException
from app.iam.application.ports.repositories import (
    TeacherRepository,
    UserRepository,
)
from app.iam.application.results.signup_result import SignupResult
from app.iam.application.services.user_command_service import (
    UserCommandServiceImpl,
)
from app.iam.application.validators.teacher_validator import TeacherValidator


class TeacherCommandServiceImpl:
    def __init__(
        self,
        user_service: UserCommandServiceImpl,
        teacher_repo: TeacherRepository,
        user_repo: UserRepository,
    ) -> None:
        self._user_service = user_service
        self._teacher_repo = teacher_repo
        self._user_repo = user_repo

    def signup(self, context: SignupContext) -> SignupResult:
        TeacherValidator.validate_signup(context)

        user_id = self._user_service.ensure_user(context)

        if context.phone:
            existing = self._teacher_repo.find_by_phone(context.phone)
            if existing:
                raise AlreadyExistsException("A teacher with this phone already exists.")

        command = SignupCommand(
            user_id=user_id,
            institute_name=context.institute_name,
            phone=context.phone,
        )
        teacher = self._teacher_repo.create(command)

        user = self._user_repo.find_by_id(user_id)

        return AuthAssembler.to_signup_result(user, teacher)
