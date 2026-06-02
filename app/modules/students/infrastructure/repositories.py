from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment_session import AssessmentSession
from app.models.classroom import Classroom
from app.modules.students.domain.entities import StudentData
from app.modules.students.infrastructure.models import Student
from app.services.audit import create_audit_log


class SQLAlchemyStudentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_classroom(self, classroom_id: UUID) -> Classroom | None:
        return self.db.get(Classroom, classroom_id)

    def list_by_classroom(self, classroom_id: UUID) -> list[Student]:
        query = select(Student).where(Student.classroom_id == classroom_id).order_by(Student.created_at.desc())
        return list(self.db.scalars(query))

    def get_by_id(self, student_id: UUID) -> Student | None:
        return self.db.get(Student, student_id)

    def code_exists(self, *, classroom_id: UUID, code: str, exclude_student_id: UUID | None = None) -> bool:
        query = select(Student).where(Student.classroom_id == classroom_id, Student.code == code)
        if exclude_student_id is not None:
            query = query.where(Student.id != exclude_student_id)
        return self.db.scalar(query) is not None

    def create_student(self, *, classroom_id: UUID, student_data: StudentData) -> Student:
        return Student(classroom_id=classroom_id, **student_data.__dict__)

    def add(self, student: Student) -> None:
        self.db.add(student)

    def list_sessions(self, student_id: UUID) -> list[AssessmentSession]:
        query = select(AssessmentSession).where(AssessmentSession.student_id == student_id).order_by(AssessmentSession.created_at.desc())
        return list(self.db.scalars(query))

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        create_audit_log(self.db, user=user, action=action, entity_type=entity_type, entity_id=entity_id)

    def flush(self) -> None:
        self.db.flush()
