from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.audio_sample import AudioSample
from app.models.classroom import Classroom
from app.models.exercise import Exercise
from app.models.student import Student
from app.models.writing_sample import WritingSample
from app.assessment.modules.assessment_sessions.domain.entities import AssessmentSessionData
from app.assessment.modules.assessment_sessions.infrastructure.models import AssessmentSession
from app.services.audit import create_audit_log


class SQLAlchemyAssessmentSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_student(self, student_id: UUID) -> Student | None:
        return self.db.get(Student, student_id)

    def get_student_classroom(self, student: Student) -> Classroom | None:
        return self.db.get(Classroom, student.classroom_id)

    def get_exercise(self, exercise_id: UUID) -> Exercise | None:
        return self.db.get(Exercise, exercise_id)

    def get_session(self, session_id: UUID) -> AssessmentSession | None:
        return self.db.get(AssessmentSession, session_id)

    def get_session_with_details(self, session_id: UUID) -> AssessmentSession | None:
        query = (
            select(AssessmentSession)
            .where(AssessmentSession.id == session_id)
            .options(
                joinedload(AssessmentSession.writing_sample).joinedload(WritingSample.analysis),
                joinedload(AssessmentSession.audio_sample).joinedload(AudioSample.analysis),
                joinedload(AssessmentSession.result),
            )
        )
        return self.db.scalar(query)

    def list_by_student(self, student_id: UUID) -> list[AssessmentSession]:
        query = (
            select(AssessmentSession)
            .where(AssessmentSession.student_id == student_id)
            .order_by(AssessmentSession.created_at.desc())
        )
        return list(self.db.scalars(query))

    def create_session(self, session_data: AssessmentSessionData) -> AssessmentSession:
        return AssessmentSession(
            student_id=session_data.student_id,
            exercise_id=session_data.exercise_id,
            teacher_profile_id=session_data.teacher_profile_id,
            status=session_data.status,
        )

    def add(self, session: AssessmentSession) -> None:
        self.db.add(session)

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        create_audit_log(self.db, user=user, action=action, entity_type=entity_type, entity_id=entity_id)

    def flush(self) -> None:
        self.db.flush()
