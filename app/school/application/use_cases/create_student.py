from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.school.application.assemblers.student_assembler import StudentAssembler
from app.school.application.exceptions.student_exceptions import DuplicateStudentCodeError
from app.school.application.ports.student_repository import StudentRepository
from app.school.application.results.student_result import StudentResult
from app.school.domain.enums import Gender
from app.school.domain.student import Student


@dataclass
class CreateStudentCommand:
    classroom_id: UUID
    code: str
    age: int
    gender: Gender


class CreateStudentUseCase:
    def __init__(self, student_repo: StudentRepository) -> None:
        self._student_repo = student_repo

    def execute(self, command: CreateStudentCommand) -> StudentResult:
        existing = self._student_repo.find_by_code_in_classroom(command.code, command.classroom_id)
        if existing:
            raise DuplicateStudentCodeError()

        now = datetime.now(timezone.utc)
        student = self._student_repo.create(
            Student(
                id=UUID(int=0),
                classroom_id=command.classroom_id,
                code=command.code,
                age=command.age,
                gender=command.gender,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

        return StudentAssembler.to_result(student)
