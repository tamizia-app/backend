from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from app.school.application.assemblers.classroom_assembler import ClassroomAssembler
from app.school.application.exceptions.classroom_exceptions import (
    ClassroomNotFoundError,
    DuplicateClassNameError,
)
from app.school.application.ports.classroom_repository import ClassroomRepository
from app.school.application.results.classroom_result import ClassroomResult
from app.school.domain.classroom import Classroom
from app.school.domain.enums import GradeLevel, Section


@dataclass
class UpdateClassroomCommand:
    classroom_id: UUID
    homeroom_teacher_id: UUID
    name: str
    grade_level: GradeLevel
    section: Section
    school_year: date


class UpdateClassroomUseCase:
    def __init__(self, classroom_repo: ClassroomRepository) -> None:
        self._classroom_repo = classroom_repo

    def execute(self, command: UpdateClassroomCommand) -> ClassroomResult:
        existing = self._classroom_repo.find_by_id(command.classroom_id)
        if not existing:
            raise ClassroomNotFoundError()

        same_name = self._classroom_repo.find_by_name_and_teacher(command.name, command.homeroom_teacher_id)
        if same_name and same_name.id != command.classroom_id:
            raise DuplicateClassNameError()

        now = datetime.now(timezone.utc)
        updated = self._classroom_repo.update(
            Classroom(
                id=existing.id,
                homeroom_teacher_id=existing.homeroom_teacher_id,
                name=command.name,
                grade_level=command.grade_level,
                section=command.section,
                school_year=command.school_year,
                is_active=existing.is_active,
                created_at=existing.created_at,
                updated_at=now,
            )
        )

        return ClassroomAssembler.to_result(updated)
