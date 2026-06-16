from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.assessment.modules.assessment_sessions.application._access import (
    get_accessible_student,
    get_active_exercise,
    teacher_profile_id_for,
)
from app.assessment.modules.assessment_sessions.domain.entities import AssessmentSessionData
from app.assessment.modules.assessment_sessions.domain.repositories import AssessmentSessionRepository


@dataclass(frozen=True)
class CreateSessionCommand:
    student_id: UUID
    exercise_id: UUID
    current_user: Any


class CreateSessionUseCase:
    def __init__(self, repository: AssessmentSessionRepository) -> None:
        self.repository = repository

    def execute(self, command: CreateSessionCommand):
        student = get_accessible_student(self.repository, student_id=command.student_id, current_user=command.current_user)
        get_active_exercise(self.repository, exercise_id=command.exercise_id)

        session = self.repository.create_session(
            AssessmentSessionData(
                student_id=student.id,
                exercise_id=command.exercise_id,
                teacher_profile_id=teacher_profile_id_for(command.current_user),
            )
        )
        self.repository.add(session)
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="create_session",
            entity_type="assessment_session",
            entity_id=session.id,
        )
        return session

