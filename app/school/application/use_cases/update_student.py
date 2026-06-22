from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.school.application.assemblers.student_assembler import StudentAssembler
from app.school.application.exceptions.student_exceptions import DuplicateStudentCodeError, StudentNotFoundError
from app.school.application.ports.student_repository import StudentRepository
from app.school.application.results.student_result import StudentResult
from app.school.domain.enums import Gender
from app.school.domain.student import Student


@dataclass
class UpdateStudentCommand:
    student_id: UUID
    code: str
    age: int
    gender: Gender


class UpdateStudentUseCase:
    def __init__(self, student_repo: StudentRepository) -> None:
        self._student_repo = student_repo

    def execute(self, command: UpdateStudentCommand) -> StudentResult:
        existing = self._student_repo.find_by_id(command.student_id)
        if not existing:
            raise StudentNotFoundError()

        same_code = self._student_repo.find_by_code_in_classroom(
            command.code, existing.classroom_id, exclude_id=command.student_id
        )
        if same_code:
            raise DuplicateStudentCodeError()

        now = datetime.now(timezone.utc)
        updated = self._student_repo.update(
            Student(
                id=existing.id,
                classroom_id=existing.classroom_id,
                code=command.code,
                age=command.age,
                gender=command.gender,
                is_active=existing.is_active,
                created_at=existing.created_at,
                updated_at=now,
            )
        )

        return StudentAssembler.to_result(updated)
