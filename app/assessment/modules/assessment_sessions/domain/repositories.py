from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.assessment.modules.assessment_sessions.domain.entities import AssessmentSessionData


class AssessmentSessionRepository(Protocol):
    def get_student(self, student_id: UUID) -> Any | None:
        ...

    def get_student_classroom(self, student: Any) -> Any | None:
        ...

    def get_exercise(self, exercise_id: UUID) -> Any | None:
        ...

    def get_session(self, session_id: UUID) -> Any | None:
        ...

    def get_session_with_details(self, session_id: UUID) -> Any | None:
        ...

    def list_by_student(self, student_id: UUID) -> list[Any]:
        ...

    def create_session(self, session_data: AssessmentSessionData) -> Any:
        ...

    def add(self, session: Any) -> None:
        ...

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        ...

    def flush(self) -> None:
        ...

