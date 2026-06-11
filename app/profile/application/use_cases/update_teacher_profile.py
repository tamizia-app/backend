from dataclasses import dataclass
from uuid import UUID

from app.profile.application.assemblers.teacher_assembler import TeacherAssembler
from app.profile.application.exceptions.profile_exceptions import (
    TeacherNotFoundError,
    UserNotFoundError,
)
from app.profile.application.ports.repositories import TeacherRepository
from app.profile.application.ports.user_management_port import UserManagementPort
from app.profile.application.results.teacher_result import TeacherResult
from app.profile.domain.teacher import Teacher


@dataclass
class UpdateTeacherCommand:
    user_id: UUID
    name: str
    lastname: str
    email: str
    institute_name: str | None
    phone: str | None


class UpdateTeacherProfileUseCase:
    def __init__(
        self,
        teacher_repo: TeacherRepository,
        user_management: UserManagementPort,
    ) -> None:
        self._teacher_repo = teacher_repo
        self._user_management = user_management

    def execute(self, command: UpdateTeacherCommand) -> TeacherResult:
        existing = self._teacher_repo.find_by_user_id(command.user_id)
        if not existing:
            raise TeacherNotFoundError()

        self._user_management.update_user(
            command.user_id,
            name=command.name,
            lastname=command.lastname,
            email=command.email,
        )

        updated = self._teacher_repo.update(
            Teacher(
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

        return TeacherAssembler.to_result(updated, user)
