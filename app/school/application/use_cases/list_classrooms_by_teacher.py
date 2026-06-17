from dataclasses import dataclass
from uuid import UUID

from app.school.application.assemblers.classroom_assembler import ClassroomAssembler
from app.school.application.ports.classroom_repository import ClassroomRepository
from app.school.application.results.classroom_result import ClassroomResult


@dataclass
class ListClassroomsByTeacherQuery:
    homeroom_teacher_id: UUID


class ListClassroomsByTeacherUseCase:
    def __init__(self, classroom_repo: ClassroomRepository) -> None:
        self._classroom_repo = classroom_repo

    def execute(self, query: ListClassroomsByTeacherQuery) -> list[ClassroomResult]:
        classrooms = self._classroom_repo.find_by_teacher_id(query.homeroom_teacher_id)
        return [ClassroomAssembler.to_result(c) for c in classrooms]
