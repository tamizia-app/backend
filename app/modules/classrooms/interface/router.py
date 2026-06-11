from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.iam.infrastructure.models.user_model import UserModel
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
from app.modules.classrooms.interface.schemas import ClassroomCreate, ClassroomResponse, ClassroomUpdate
from app.schemas.student import StudentCreate, StudentResponse
from app.services import students as student_service


router = APIRouter(prefix="/classrooms")


def get_classroom_repository(db: Session = Depends(get_db)) -> SQLAlchemyClassroomRepository:
    return SQLAlchemyClassroomRepository(db)


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


@router.get("", response_model=list[ClassroomResponse])
def list_classrooms(
    repository: SQLAlchemyClassroomRepository = Depends(get_classroom_repository),
    current_user: UserModel = Depends(get_current_user),
) -> list[ClassroomResponse]:
    try:
        return ListClassroomsUseCase(repository).execute(ListClassroomsQuery(current_user=current_user))
    except ClassroomError as error:
        _raise_http_error(error)


@router.post("", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
def create_classroom(
    payload: ClassroomCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ClassroomResponse:
    repository = SQLAlchemyClassroomRepository(db)
    try:
        classroom = CreateClassroomUseCase(repository).execute(
            CreateClassroomCommand(
                classroom_data=_classroom_data_from_payload(payload),
                current_user=current_user,
            )
        )
    except ClassroomError as error:
        _raise_http_error(error)

    db.commit()
    db.refresh(classroom)
    return classroom


@router.get("/{classroom_id}", response_model=ClassroomResponse)
def get_classroom(
    classroom_id: UUID,
    repository: SQLAlchemyClassroomRepository = Depends(get_classroom_repository),
    current_user: UserModel = Depends(get_current_user),
) -> ClassroomResponse:
    try:
        return GetClassroomUseCase(repository).execute(
            GetClassroomQuery(classroom_id=classroom_id, current_user=current_user)
        )
    except ClassroomError as error:
        _raise_http_error(error)


@router.patch("/{classroom_id}", response_model=ClassroomResponse)
def update_classroom(
    classroom_id: UUID,
    payload: ClassroomUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ClassroomResponse:
    repository = SQLAlchemyClassroomRepository(db)
    try:
        classroom = UpdateClassroomUseCase(repository).execute(
            UpdateClassroomCommand(
                classroom_id=classroom_id,
                changes=payload.model_dump(exclude_unset=True),
                current_user=current_user,
            )
        )
    except ClassroomError as error:
        _raise_http_error(error)

    db.commit()
    db.refresh(classroom)
    return classroom


@router.get("/{classroom_id}/students", response_model=list[StudentResponse])
def list_students_by_classroom(
    classroom_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[StudentResponse]:
    return student_service.list_students_by_classroom(db, classroom_id=classroom_id, current_user=current_user)


@router.post("/{classroom_id}/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    classroom_id: UUID,
    payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentResponse:
    student = student_service.create_student(db, classroom_id=classroom_id, current_user=current_user, payload=payload)
    db.commit()
    db.refresh(student)
    return student
