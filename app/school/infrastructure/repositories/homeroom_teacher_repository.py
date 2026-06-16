from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.school.application.ports.repositories import HomeroomTeacherRepository
from app.school.domain.homeroom_teacher import HomeroomTeacher
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel


class SQLAlchemyHomeroomTeacherRepository(HomeroomTeacherRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_user_id(self, user_id: UUID) -> HomeroomTeacher | None:
        model = self._db.scalar(select(HomeroomTeacherModel).where(HomeroomTeacherModel.user_id == user_id))
        return self._to_domain(model) if model else None

    def find_by_id(self, teacher_id: UUID) -> HomeroomTeacher | None:
        model = self._db.get(HomeroomTeacherModel, teacher_id)
        return self._to_domain(model) if model else None

    def create(self, teacher: HomeroomTeacher) -> HomeroomTeacher:
        model = HomeroomTeacherModel(
            user_id=teacher.user_id,
            institute_name=teacher.institute_name,
            phone=teacher.phone,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, teacher: HomeroomTeacher) -> HomeroomTeacher:
        model = self._db.get(HomeroomTeacherModel, teacher.id)
        if model:
            model.institute_name = teacher.institute_name
            model.phone = teacher.phone
            self._db.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: HomeroomTeacherModel) -> HomeroomTeacher:
        return HomeroomTeacher(
            id=model.id,
            user_id=model.user_id,
            institute_name=model.institute_name,
            phone=model.phone,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
