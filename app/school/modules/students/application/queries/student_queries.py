from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class GetStudentQuery:
    student_id: UUID
    current_user: Any


@dataclass(frozen=True)
class ListStudentsByClassroomQuery:
    classroom_id: UUID
    current_user: Any


@dataclass(frozen=True)
class ListStudentSessionsQuery:
    student_id: UUID
    current_user: Any

