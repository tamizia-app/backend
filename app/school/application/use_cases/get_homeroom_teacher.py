from uuid import UUID

from app.school.application.assemblers.homeroom_teacher_assembler import HomeroomTeacherAssembler
from app.school.application.exceptions.school_exceptions import (
    HomeroomTeacherNotFoundError,
    UserNotFoundError,
)
from app.school.application.ports.repositories import HomeroomTeacherRepository
from app.school.application.ports.user_management_port import UserManagementPort
from app.school.application.results.homeroom_teacher_result import HomeroomTeacherResult


class GetHomeroomTeacherUseCase:
    def __init__(
        self,
        teacher_repo: HomeroomTeacherRepository,
        user_management: UserManagementPort,
    ) -> None:
        self._teacher_repo = teacher_repo
        self._user_management = user_management

    def execute(self, user_id: UUID) -> HomeroomTeacherResult:
        user = self._user_management.get_user(user_id)
        if not user:
            raise UserNotFoundError()

        teacher = self._teacher_repo.find_by_user_id(user_id)
        if not teacher:
            raise HomeroomTeacherNotFoundError()

        return HomeroomTeacherAssembler.to_result(teacher, user)
