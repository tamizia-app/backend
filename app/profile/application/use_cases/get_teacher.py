from uuid import UUID

from app.profile.application.assemblers.teacher_assembler import TeacherAssembler
from app.profile.application.exceptions.profile_exceptions import (
    TeacherNotFoundError,
    UserNotFoundError,
)
from app.profile.application.ports.repositories import TeacherRepository
from app.profile.application.ports.user_management_port import UserManagementPort
from app.profile.application.results.teacher_result import TeacherResult


class GetTeacherUseCase:
    def __init__(
        self,
        teacher_repo: TeacherRepository,
        user_management: UserManagementPort,
    ) -> None:
        self._teacher_repo = teacher_repo
        self._user_management = user_management

    def execute(self, user_id: UUID) -> TeacherResult:
        user = self._user_management.get_user(user_id)
        if not user:
            raise UserNotFoundError()

        teacher = self._teacher_repo.find_by_user_id(user_id)
        if not teacher:
            raise TeacherNotFoundError()

        return TeacherAssembler.to_result(teacher, user)
