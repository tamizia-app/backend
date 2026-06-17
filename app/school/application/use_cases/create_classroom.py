from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from app.school.application.assemblers.classroom_assembler import ClassroomAssembler
from app.school.application.exceptions.classroom_exceptions import (
    DuplicateClassNameError,
)
from app.school.application.ports.classroom_repository import ClassroomRepository
from app.school.application.results.classroom_result import ClassroomResult
from app.school.domain.classroom import Classroom
from app.school.domain.enums import GradeLevel, Section


@dataclass
class CreateClassroomCommand:
    homeroom_teacher_id: UUID
    name: str
    grade_level: GradeLevel
    section: Section
    school_year: date


class CreateClassroomUseCase:
    def __init__(self, classroom_repo: ClassroomRepository) -> None:
        self._classroom_repo = classroom_repo

    def execute(self, command: CreateClassroomCommand) -> ClassroomResult:
        existing = self._classroom_repo.find_by_name_and_teacher(command.name, command.homeroom_teacher_id)
        if existing:
            raise DuplicateClassNameError()

        now = datetime.now(timezone.utc)
        classroom = self._classroom_repo.create(
            Classroom(
                id=UUID(int=0),
                homeroom_teacher_id=command.homeroom_teacher_id,
                name=command.name,
                grade_level=command.grade_level,
                section=command.section,
                school_year=command.school_year,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

        return ClassroomAssembler.to_result(classroom)
