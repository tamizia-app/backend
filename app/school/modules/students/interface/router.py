from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.iam.infrastructure.models.user_model import UserModel
from app.school.modules.students.application.commands.student_commands import UpdateStudentCommand
from app.school.modules.students.application.queries.student_queries import GetStudentQuery, ListStudentSessionsQuery
from app.school.modules.students.application.services import GetStudentUseCase, ListStudentSessionsUseCase, UpdateStudentUseCase
from app.school.modules.students.domain.exceptions import (
    ClassroomNotFoundError,
    StudentCodeAlreadyExistsError,
    StudentError,
    StudentNotBelongsToTeacherError,
    StudentNotFoundError,
    TeacherProfileMissingError,
)
from app.school.modules.students.infrastructure.repositories import SQLAlchemyStudentRepository
from app.school.modules.students.interface.schemas import StudentResponse, StudentUpdate
from app.schemas.session import SessionResponse


router = APIRouter(prefix="/students")


def get_student_repository(db: Session = Depends(get_db)) -> SQLAlchemyStudentRepository:
    return SQLAlchemyStudentRepository(db)


def _raise_http_error(error: StudentError) -> None:
    if isinstance(error, StudentCodeAlreadyExistsError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student code already exists in classroom.",
        ) from error
    if isinstance(error, TeacherProfileMissingError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher profile not configured.",
        ) from error
    if isinstance(error, ClassroomNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found.") from error
    if isinstance(error, (StudentNotFoundError, StudentNotBelongsToTeacherError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.") from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student operation failed.") from error


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: UUID,
    repository: SQLAlchemyStudentRepository = Depends(get_student_repository),
    current_user: UserModel = Depends(get_current_user),
) -> StudentResponse:
    try:
        return GetStudentUseCase(repository).execute(GetStudentQuery(student_id=student_id, current_user=current_user))
    except StudentError as error:
        _raise_http_error(error)


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentResponse:
    repository = SQLAlchemyStudentRepository(db)
    try:
        student = UpdateStudentUseCase(repository).execute(
            UpdateStudentCommand(
                student_id=student_id,
                changes=payload.model_dump(exclude_unset=True),
                current_user=current_user,
            )
        )
    except StudentError as error:
        _raise_http_error(error)

    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}/sessions", response_model=list[SessionResponse])
def list_sessions_by_student(
    student_id: UUID,
    repository: SQLAlchemyStudentRepository = Depends(get_student_repository),
    current_user: UserModel = Depends(get_current_user),
) -> list[SessionResponse]:
    try:
        return ListStudentSessionsUseCase(repository).execute(
            ListStudentSessionsQuery(student_id=student_id, current_user=current_user)
        )
    except StudentError as error:
        _raise_http_error(error)

