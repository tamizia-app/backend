from dataclasses import dataclass
from uuid import UUID

from app.school.application.assemblers.classroom_assembler import ClassroomAssembler
from app.school.application.exceptions.classroom_exceptions import (
    ClassroomNotFoundError,
)
from app.school.application.ports.classroom_repository import ClassroomRepository
from app.school.application.results.classroom_result import ClassroomResult


@dataclass
class GetClassroomQuery:
    classroom_id: UUID


class GetClassroomUseCase:
    def __init__(self, classroom_repo: ClassroomRepository) -> None:
        self._classroom_repo = classroom_repo

    def execute(self, query: GetClassroomQuery) -> ClassroomResult:
        classroom = self._classroom_repo.find_by_id(query.classroom_id)
        if not classroom:
            raise ClassroomNotFoundError()
        return ClassroomAssembler.to_result(classroom)
