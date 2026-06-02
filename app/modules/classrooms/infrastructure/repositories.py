from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.classrooms.domain.entities import ClassroomData
from app.modules.classrooms.infrastructure.models import Classroom
from app.services.audit import create_audit_log


class SQLAlchemyClassroomRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Classroom]:
        query = select(Classroom).order_by(Classroom.created_at.desc())
        return list(self.db.scalars(query))

    def list_by_teacher(self, teacher_profile_id: UUID) -> list[Classroom]:
        query = (
            select(Classroom)
            .where(Classroom.teacher_profile_id == teacher_profile_id)
            .order_by(Classroom.created_at.desc())
        )
        return list(self.db.scalars(query))

    def get_by_id(self, classroom_id: UUID) -> Classroom | None:
        return self.db.get(Classroom, classroom_id)

    def create_classroom(self, *, teacher_profile_id: UUID, classroom_data: ClassroomData) -> Classroom:
        return Classroom(teacher_profile_id=teacher_profile_id, **classroom_data.__dict__)

    def add(self, classroom: Classroom) -> None:
        self.db.add(classroom)

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        create_audit_log(self.db, user=user, action=action, entity_type=entity_type, entity_id=entity_id)

    def flush(self) -> None:
        self.db.flush()

