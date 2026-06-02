from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.user import User
from app.modules.students.application.commands.student_commands import CreateStudentCommand, UpdateStudentCommand
from app.modules.students.application.queries.student_queries import GetStudentQuery, ListStudentsByClassroomQuery
from app.modules.students.application.services import (
    CreateStudentUseCase,
    GetStudentUseCase,
    ListStudentsByClassroomUseCase,
    UpdateStudentUseCase,
)
from app.modules.students.domain.entities import StudentData
from app.modules.students.domain.exceptions import (
    ClassroomNotFoundError,
    StudentCodeAlreadyExistsError,
    StudentError,
    StudentNotBelongsToTeacherError,
    StudentNotFoundError,
    TeacherProfileMissingError,
)
from app.modules.students.infrastructure.repositories import SQLAlchemyStudentRepository
from app.schemas.student import StudentCreate, StudentUpdate


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


def list_students_by_classroom(db: Session, *, classroom_id, current_user: User) -> list[Student]:
    try:
        return ListStudentsByClassroomUseCase(SQLAlchemyStudentRepository(db)).execute(
            ListStudentsByClassroomQuery(classroom_id=classroom_id, current_user=current_user)
        )
    except StudentError as error:
        _raise_http_error(error)


def create_student(db: Session, *, classroom_id, current_user: User, payload: StudentCreate) -> Student:
    try:
        return CreateStudentUseCase(SQLAlchemyStudentRepository(db)).execute(
            CreateStudentCommand(
                classroom_id=classroom_id,
                student_data=StudentData(
                    code=payload.code,
                    first_name=payload.first_name,
                    last_name=payload.last_name,
                    age=payload.age,
                ),
                current_user=current_user,
            )
        )
    except StudentError as error:
        _raise_http_error(error)


def get_student_for_user(db: Session, student_id, current_user: User) -> Student:
    try:
        return GetStudentUseCase(SQLAlchemyStudentRepository(db)).execute(
            GetStudentQuery(student_id=student_id, current_user=current_user)
        )
    except StudentError as error:
        _raise_http_error(error)


def update_student(db: Session, *, student: Student, current_user: User, payload: StudentUpdate) -> Student:
    try:
        return UpdateStudentUseCase(SQLAlchemyStudentRepository(db)).execute(
            UpdateStudentCommand(
                student_id=student.id,
                changes=payload.model_dump(exclude_unset=True),
                current_user=current_user,
            )
        )
    except StudentError as error:
        _raise_http_error(error)
