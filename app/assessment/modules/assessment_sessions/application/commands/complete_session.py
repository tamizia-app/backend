from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.domain.enums import SessionStatus
from app.assessment.modules.assessment_sessions.application._access import get_accessible_session
from app.assessment.modules.assessment_sessions.domain.entities import can_complete_session
from app.assessment.modules.assessment_sessions.domain.exceptions import InvalidSessionStateError
from app.assessment.modules.assessment_sessions.domain.repositories import AssessmentSessionRepository


@dataclass(frozen=True)
class CompleteSessionCommand:
    session_id: UUID
    current_user: Any


class CompleteSessionUseCase:
    def __init__(self, repository: AssessmentSessionRepository) -> None:
        self.repository = repository

    def execute(self, command: CompleteSessionCommand):
        session = get_accessible_session(self.repository, session_id=command.session_id, current_user=command.current_user)
        if not can_complete_session(session.status):
            raise InvalidSessionStateError()

        completed_at = datetime.now(UTC)
        session.completed_at = completed_at
        session.status = SessionStatus.COMPLETED
        if session.started_at:
            session.duration_seconds = int((completed_at - session.started_at).total_seconds())
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="complete_session",
            entity_type="assessment_session",
            entity_id=session.id,
        )
        return session

