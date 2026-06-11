from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.profile.application.ports.repositories import TeacherRepository
from app.profile.domain.teacher import Teacher
from app.profile.infrastructure.models.teacher_model import TeacherModel


class SQLAlchemyTeacherRepository(TeacherRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_user_id(self, user_id: UUID) -> Teacher | None:
        model = self._db.scalar(select(TeacherModel).where(TeacherModel.user_id == user_id))
        return self._to_domain(model) if model else None

    def find_by_id(self, teacher_id: UUID) -> Teacher | None:
        model = self._db.get(TeacherModel, teacher_id)
        return self._to_domain(model) if model else None

    def create(self, teacher: Teacher) -> Teacher:
        model = TeacherModel(
            user_id=teacher.user_id,
            institute_name=teacher.institute_name,
            phone=teacher.phone,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, teacher: Teacher) -> Teacher:
        model = self._db.get(TeacherModel, teacher.id)
        if model:
            model.institute_name = teacher.institute_name
            model.phone = teacher.phone
            self._db.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: TeacherModel) -> Teacher:
        return Teacher(
            id=model.id,
            user_id=model.user_id,
            institute_name=model.institute_name,
            phone=model.phone,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
