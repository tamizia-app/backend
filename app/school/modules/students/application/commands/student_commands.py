from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.school.modules.students.domain.entities import StudentData


@dataclass(frozen=True)
class CreateStudentCommand:
    classroom_id: UUID
    student_data: StudentData
    current_user: Any


@dataclass(frozen=True)
class UpdateStudentCommand:
    student_id: UUID
    changes: dict[str, Any]
    current_user: Any

