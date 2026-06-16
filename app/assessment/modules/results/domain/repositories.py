from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class ResultRepository(Protocol):
    def create_or_update_session_result(self, *, session: Any, scores: Any) -> Any:
        ...

    def get_by_session(self, session_id: UUID) -> Any | None:
        ...

    def list_by_student(self, student_id: UUID) -> list[Any]:
        ...

    def add(self, result: Any) -> None:
        ...

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        ...

    def flush(self) -> None:
        ...

