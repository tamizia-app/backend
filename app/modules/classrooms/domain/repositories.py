from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.modules.classrooms.domain.entities import ClassroomData


class ClassroomRepository(Protocol):
    def list_all(self) -> list[Any]:
        ...

    def list_by_teacher(self, teacher_profile_id: UUID) -> list[Any]:
        ...

    def get_by_id(self, classroom_id: UUID) -> Any | None:
        ...

    def create_classroom(self, *, teacher_profile_id: UUID, classroom_data: ClassroomData) -> Any:
        ...

    def add(self, classroom: Any) -> None:
        ...

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        ...

    def flush(self) -> None:
        ...

