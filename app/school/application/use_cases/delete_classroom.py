from dataclasses import dataclass
from uuid import UUID

from app.school.application.exceptions.classroom_exceptions import (
    ClassroomNotFoundError,
)
from app.school.application.ports.classroom_repository import ClassroomRepository


@dataclass
class DeleteClassroomCommand:
    classroom_id: UUID


class DeleteClassroomUseCase:
    def __init__(self, classroom_repo: ClassroomRepository) -> None:
        self._classroom_repo = classroom_repo

    def execute(self, command: DeleteClassroomCommand) -> None:
        existing = self._classroom_repo.find_by_id(command.classroom_id)
        if not existing:
            raise ClassroomNotFoundError()
        self._classroom_repo.delete(command.classroom_id)
