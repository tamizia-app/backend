from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.classroom import Classroom
from app.models.user import User
from app.modules.classrooms.application.commands.classroom_commands import CreateClassroomCommand, UpdateClassroomCommand
from app.modules.classrooms.application.queries.classroom_queries import GetClassroomQuery, ListClassroomsQuery
from app.modules.classrooms.application.services import (
    CreateClassroomUseCase,
    GetClassroomUseCase,
    ListClassroomsUseCase,
    UpdateClassroomUseCase,
)
from app.modules.classrooms.domain.entities import ClassroomData
from app.modules.classrooms.domain.exceptions import (
    ClassroomError,
    ClassroomNotBelongsToTeacherError,
    ClassroomNotFoundError,
    TeacherProfileMissingError,
)
from app.modules.classrooms.infrastructure.repositories import SQLAlchemyClassroomRepository
from app.schemas.classroom import ClassroomCreate, ClassroomUpdate


def _raise_http_error(error: ClassroomError) -> None:
    if isinstance(error, TeacherProfileMissingError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher profile not configured.",
        ) from error
    if isinstance(error, (ClassroomNotFoundError, ClassroomNotBelongsToTeacherError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found.") from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Classroom operation failed.") from error


def _classroom_data_from_payload(payload: ClassroomCreate) -> ClassroomData:
    return ClassroomData(
        name=payload.name,
        grade_level=payload.grade_level,
        section=payload.section,
        school_year=payload.school_year,
    )


def list_classrooms(db: Session, current_user: User) -> list[Classroom]:
    try:
        return ListClassroomsUseCase(SQLAlchemyClassroomRepository(db)).execute(
            ListClassroomsQuery(current_user=current_user)
        )
    except ClassroomError as error:
        _raise_http_error(error)


def create_classroom(db: Session, current_user: User, payload: ClassroomCreate) -> Classroom:
    try:
        return CreateClassroomUseCase(SQLAlchemyClassroomRepository(db)).execute(
            CreateClassroomCommand(
                classroom_data=_classroom_data_from_payload(payload),
                current_user=current_user,
            )
        )
    except ClassroomError as error:
        _raise_http_error(error)


def get_classroom_for_user(db: Session, classroom_id, current_user: User) -> Classroom:
    try:
        return GetClassroomUseCase(SQLAlchemyClassroomRepository(db)).execute(
            GetClassroomQuery(classroom_id=classroom_id, current_user=current_user)
        )
    except ClassroomError as error:
        _raise_http_error(error)


def update_classroom(db: Session, classroom: Classroom, payload: ClassroomUpdate, current_user: User) -> Classroom:
    try:
        return UpdateClassroomUseCase(SQLAlchemyClassroomRepository(db)).execute(
            UpdateClassroomCommand(
                classroom_id=classroom.id,
                changes=payload.model_dump(exclude_unset=True),
                current_user=current_user,
            )
        )
    except ClassroomError as error:
        _raise_http_error(error)
