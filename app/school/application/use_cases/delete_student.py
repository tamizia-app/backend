from dataclasses import dataclass
from uuid import UUID

from app.school.application.exceptions.student_exceptions import StudentNotFoundError
from app.school.application.ports.student_repository import StudentRepository


@dataclass
class DeleteStudentCommand:
    student_id: UUID


class DeleteStudentUseCase:
    def __init__(self, student_repo: StudentRepository) -> None:
        self._student_repo = student_repo

    def execute(self, command: DeleteStudentCommand) -> None:
        existing = self._student_repo.find_by_id(command.student_id)
        if not existing:
            raise StudentNotFoundError()
        self._student_repo.delete(command.student_id)
