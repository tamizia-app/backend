from dataclasses import dataclass
from uuid import UUID

from app.school.application.assemblers.homeroom_teacher_assembler import HomeroomTeacherAssembler
from app.school.application.exceptions.school_exceptions import (
    HomeroomTeacherNotFoundError,
    UserNotFoundError,
)
from app.school.application.ports.repositories import HomeroomTeacherRepository
from app.school.application.ports.user_management_port import UserManagementPort
from app.school.application.results.homeroom_teacher_result import HomeroomTeacherResult
from app.school.domain.homeroom_teacher import HomeroomTeacher


@dataclass
class UpdateHomeroomTeacherCommand:
    user_id: UUID
    name: str
    lastname: str
    email: str
    institute_name: str | None
    phone: str | None


class UpdateHomeroomTeacherUseCase:
    def __init__(
        self,
        teacher_repo: HomeroomTeacherRepository,
        user_management: UserManagementPort,
    ) -> None:
        self._teacher_repo = teacher_repo
        self._user_management = user_management

    def execute(self, command: UpdateHomeroomTeacherCommand) -> HomeroomTeacherResult:
        existing = self._teacher_repo.find_by_user_id(command.user_id)
        if not existing:
            raise HomeroomTeacherNotFoundError()

        self._user_management.update_user(
            command.user_id,
            name=command.name,
            lastname=command.lastname,
            email=command.email,
        )

        updated = self._teacher_repo.update(
            HomeroomTeacher(
                id=existing.id,
                user_id=existing.user_id,
                institute_name=command.institute_name,
                phone=command.phone,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
            )
        )

        user = self._user_management.get_user(command.user_id)
        if not user:
            raise UserNotFoundError()

        return HomeroomTeacherAssembler.to_result(updated, user)
