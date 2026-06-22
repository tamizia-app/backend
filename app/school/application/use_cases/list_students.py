from dataclasses import dataclass
from uuid import UUID

from app.school.application.assemblers.student_assembler import StudentAssembler
from app.school.application.ports.student_repository import StudentRepository
from app.school.application.results.student_result import StudentResult


@dataclass
class ListStudentsQuery:
    classroom_id: UUID


class ListStudentsUseCase:
    def __init__(self, student_repo: StudentRepository) -> None:
        self._student_repo = student_repo

    def execute(self, query: ListStudentsQuery) -> list[StudentResult]:
        students = self._student_repo.find_by_classroom_id(query.classroom_id)
        return [StudentAssembler.to_result(s) for s in students]
