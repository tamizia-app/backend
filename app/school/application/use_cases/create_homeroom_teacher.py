from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.school.application.assemblers.homeroom_teacher_assembler import HomeroomTeacherAssembler
from app.school.application.exceptions.school_exceptions import (
    UserNotFoundError,
    ValidationError,
)
from app.school.application.ports.repositories import HomeroomTeacherRepository
from app.school.application.ports.user_management_port import UserManagementPort
from app.school.application.results.homeroom_teacher_result import HomeroomTeacherResult
from app.school.domain.homeroom_teacher import HomeroomTeacher


@dataclass
class CreateHomeroomTeacherCommand:
    user_id: UUID
    institute_name: str | None
    phone: str | None


class CreateHomeroomTeacherUseCase:
    def __init__(
        self,
        teacher_repo: HomeroomTeacherRepository,
        user_management: UserManagementPort,
    ) -> None:
        self._teacher_repo = teacher_repo
        self._user_management = user_management

    def execute(self, command: CreateHomeroomTeacherCommand) -> HomeroomTeacherResult:
        if self._teacher_repo.find_by_user_id(command.user_id):
            raise ValidationError("HomeroomTeacher already exists for this user.")

        user = self._user_management.get_user(command.user_id)
        if not user:
            raise UserNotFoundError()

        now = datetime.now(timezone.utc)
        teacher = self._teacher_repo.create(
            HomeroomTeacher(
                id=UUID(int=0),
                user_id=command.user_id,
                institute_name=command.institute_name,
                phone=command.phone,
                created_at=now,
                updated_at=now,
            )
        )

        return HomeroomTeacherAssembler.to_result(teacher, user)
