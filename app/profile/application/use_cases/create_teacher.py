from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.profile.application.assemblers.teacher_assembler import TeacherAssembler
from app.profile.application.exceptions.profile_exceptions import (
    UserNotFoundError,
    ValidationError,
)
from app.profile.application.ports.repositories import TeacherRepository
from app.profile.application.ports.user_management_port import UserManagementPort
from app.profile.application.results.teacher_result import TeacherResult
from app.profile.domain.teacher import Teacher


@dataclass
class CreateTeacherCommand:
    user_id: UUID
    institute_name: str | None
    phone: str | None


class CreateTeacherUseCase:
    def __init__(
        self,
        teacher_repo: TeacherRepository,
        user_management: UserManagementPort,
    ) -> None:
        self._teacher_repo = teacher_repo
        self._user_management = user_management

    def execute(self, command: CreateTeacherCommand) -> TeacherResult:
        if self._teacher_repo.find_by_user_id(command.user_id):
            raise ValidationError("Teacher already exists for this user.")

        user = self._user_management.get_user(command.user_id)
        if not user:
            raise UserNotFoundError()

        now = datetime.now(timezone.utc)
        teacher = self._teacher_repo.create(
            Teacher(
                id=UUID(int=0),
                user_id=command.user_id,
                institute_name=command.institute_name,
                phone=command.phone,
                created_at=now,
                updated_at=now,
            )
        )

        return TeacherAssembler.to_result(teacher, user)
