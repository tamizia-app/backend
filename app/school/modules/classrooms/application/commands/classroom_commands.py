from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.school.modules.classrooms.domain.entities import ClassroomData


@dataclass(frozen=True)
class CreateClassroomCommand:
    classroom_data: ClassroomData
    current_user: Any


@dataclass(frozen=True)
class UpdateClassroomCommand:
    classroom_id: UUID
    changes: dict[str, Any]
    current_user: Any

