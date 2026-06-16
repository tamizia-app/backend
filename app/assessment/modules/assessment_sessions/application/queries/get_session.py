from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.assessment.modules.assessment_sessions.application._access import get_accessible_session, get_accessible_student
from app.assessment.modules.assessment_sessions.domain.repositories import AssessmentSessionRepository


@dataclass(frozen=True)
class GetSessionQuery:
    session_id: UUID
    current_user: Any


@dataclass(frozen=True)
class ListSessionsByStudentQuery:
    student_id: UUID
    current_user: Any


class GetSessionUseCase:
    def __init__(self, repository: AssessmentSessionRepository) -> None:
        self.repository = repository

    def execute(self, query: GetSessionQuery):
        return get_accessible_session(
            self.repository,
            session_id=query.session_id,
            current_user=query.current_user,
            with_details=True,
        )


class ListSessionsByStudentUseCase:
    def __init__(self, repository: AssessmentSessionRepository) -> None:
        self.repository = repository

    def execute(self, query: ListSessionsByStudentQuery):
        student = get_accessible_student(self.repository, student_id=query.student_id, current_user=query.current_user)
        return self.repository.list_by_student(student.id)
