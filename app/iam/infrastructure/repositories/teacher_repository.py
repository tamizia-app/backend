from sqlalchemy import select
from sqlalchemy.orm import Session

from app.iam.application.commands.signup import SignupCommand
from app.iam.application.ports.repositories import TeacherRepository as TeacherRepositoryPort
from app.iam.domain.teacher import Teacher
from app.iam.infrastructure.mappers.model_mappers import ModelMapper
from app.iam.infrastructure.models.teacher_model import TeacherModel


class SQLAlchemyTeacherRepository(TeacherRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_phone(self, phone: str) -> Teacher | None:
        model = self._db.scalar(select(TeacherModel).where(TeacherModel.phone == phone))
        return ModelMapper.teacher_to_domain(model) if model else None

    def create(self, command: SignupCommand) -> Teacher:
        model = TeacherModel(
            user_id=command.user_id,
            institute_name=command.institute_name,
            phone=command.phone,
        )
        self._db.add(model)
        self._db.flush()
        return ModelMapper.teacher_to_domain(model)

    def exists_by_phone(self, phone: str) -> bool:
        return self._db.scalar(select(TeacherModel.id).where(TeacherModel.phone == phone)) is not None
