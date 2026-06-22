from dataclasses import dataclass
from uuid import UUID

from app.school.application.assemblers.student_assembler import StudentAssembler
from app.school.application.exceptions.student_exceptions import StudentNotFoundError
from app.school.application.ports.student_repository import StudentRepository
from app.school.application.results.student_result import StudentResult


@dataclass
class GetStudentQuery:
    student_id: UUID


class GetStudentUseCase:
    def __init__(self, student_repo: StudentRepository) -> None:
        self._student_repo = student_repo

    def execute(self, query: GetStudentQuery) -> StudentResult:
        student = self._student_repo.find_by_id(query.student_id)
        if not student:
            raise StudentNotFoundError()
        return StudentAssembler.to_result(student)
