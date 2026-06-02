from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.modules.students.domain.entities import StudentData


class StudentRepository(Protocol):
    def get_classroom(self, classroom_id: UUID) -> Any | None:
        ...

    def list_by_classroom(self, classroom_id: UUID) -> list[Any]:
        ...

    def get_by_id(self, student_id: UUID) -> Any | None:
        ...

    def code_exists(self, *, classroom_id: UUID, code: str, exclude_student_id: UUID | None = None) -> bool:
        ...

    def create_student(self, *, classroom_id: UUID, student_data: StudentData) -> Any:
        ...

    def add(self, student: Any) -> None:
        ...

    def list_sessions(self, student_id: UUID) -> list[Any]:
        ...

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        ...

    def flush(self) -> None:
        ...
