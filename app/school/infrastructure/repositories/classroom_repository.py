from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.school.application.ports.classroom_repository import ClassroomRepository
from app.school.domain.classroom import Classroom
from app.school.domain.enums import GradeLevel, Section
from app.school.infrastructure.models.classroom_model import ClassroomModel


class SQLAlchemyClassroomRepository(ClassroomRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, classroom_id: UUID) -> Classroom | None:
        model = self._db.get(ClassroomModel, classroom_id)
        return self._to_domain(model) if model else None

    def find_by_teacher_id(self, teacher_id: UUID) -> list[Classroom]:
        models = self._db.scalars(
            select(ClassroomModel).where(ClassroomModel.homeroom_teacher_id == teacher_id).order_by(ClassroomModel.name)
        )
        return [self._to_domain(m) for m in models]

    def find_by_name_and_teacher(self, name: str, teacher_id: UUID) -> Classroom | None:
        model = self._db.scalar(
            select(ClassroomModel).where(
                ClassroomModel.name == name,
                ClassroomModel.homeroom_teacher_id == teacher_id,
            )
        )
        return self._to_domain(model) if model else None

    def create(self, classroom: Classroom) -> Classroom:
        model = ClassroomModel(
            homeroom_teacher_id=classroom.homeroom_teacher_id,
            name=classroom.name,
            grade_level=classroom.grade_level.value,
            section=classroom.section.value,
            school_year=classroom.school_year,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, classroom: Classroom) -> Classroom:
        model = self._db.get(ClassroomModel, classroom.id)
        if model:
            model.name = classroom.name
            model.grade_level = classroom.grade_level.value
            model.section = classroom.section.value
            model.school_year = classroom.school_year
            self._db.flush()
        return self._to_domain(model)

    def delete(self, classroom_id: UUID) -> None:
        model = self._db.get(ClassroomModel, classroom_id)
        if model:
            self._db.delete(model)
            self._db.flush()

    @staticmethod
    def _to_domain(model: ClassroomModel) -> Classroom:
        return Classroom(
            id=model.id,
            homeroom_teacher_id=model.homeroom_teacher_id,
            name=model.name,
            grade_level=GradeLevel(model.grade_level),
            section=Section(model.section),
            school_year=model.school_year,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
