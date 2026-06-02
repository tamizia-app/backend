from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.enums import SessionStatus


@dataclass(frozen=True)
class AssessmentSessionData:
    student_id: UUID
    exercise_id: UUID
    teacher_profile_id: UUID
    status: SessionStatus = SessionStatus.PENDING


def can_start_session(status: SessionStatus) -> bool:
    return status in {SessionStatus.PENDING, SessionStatus.FAILED}


def can_complete_session(status: SessionStatus) -> bool:
    return status in {SessionStatus.PENDING, SessionStatus.IN_PROGRESS}


def can_cancel_session(status: SessionStatus) -> bool:
    return status != SessionStatus.COMPLETED

