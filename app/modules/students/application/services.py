from __future__ import annotations

from app.domain.enums import UserRole
from app.modules.students.application.commands.student_commands import CreateStudentCommand, UpdateStudentCommand
from app.modules.students.application.queries.student_queries import (
    GetStudentQuery,
    ListStudentSessionsQuery,
    ListStudentsByClassroomQuery,
)
from app.modules.students.domain.exceptions import (
    ClassroomNotFoundError,
    StudentCodeAlreadyExistsError,
    StudentNotBelongsToTeacherError,
    StudentNotFoundError,
    TeacherProfileMissingError,
)
from app.modules.students.domain.repositories import StudentRepository


def _teacher_profile_id_for(current_user):
    if not current_user.teacher_profile:
        raise TeacherProfileMissingError()
    return current_user.teacher_profile.id


def _ensure_classroom_accessible(repository: StudentRepository, *, classroom_id, current_user):
    classroom = repository.get_classroom(classroom_id)
    if not classroom:
        raise ClassroomNotFoundError()
    if current_user.role != UserRole.ADMIN and classroom.teacher_profile_id != _teacher_profile_id_for(current_user):
        raise ClassroomNotFoundError()
    return classroom


def _ensure_student_accessible(repository: StudentRepository, *, student, current_user) -> None:
    classroom = repository.get_classroom(student.classroom_id)
    if not classroom:
        raise StudentNotFoundError()
    if current_user.role != UserRole.ADMIN and classroom.teacher_profile_id != _teacher_profile_id_for(current_user):
        raise StudentNotBelongsToTeacherError()


class ListStudentsByClassroomUseCase:
    def __init__(self, repository: StudentRepository) -> None:
        self.repository = repository

    def execute(self, query: ListStudentsByClassroomQuery):
        classroom = _ensure_classroom_accessible(
            self.repository,
            classroom_id=query.classroom_id,
            current_user=query.current_user,
        )
        return self.repository.list_by_classroom(classroom.id)


class CreateStudentUseCase:
    def __init__(self, repository: StudentRepository) -> None:
        self.repository = repository

    def execute(self, command: CreateStudentCommand):
        classroom = _ensure_classroom_accessible(
            self.repository,
            classroom_id=command.classroom_id,
            current_user=command.current_user,
        )
        if self.repository.code_exists(classroom_id=classroom.id, code=command.student_data.code):
            raise StudentCodeAlreadyExistsError()

        student = self.repository.create_student(classroom_id=classroom.id, student_data=command.student_data)
        self.repository.add(student)
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="create_student",
            entity_type="student",
            entity_id=student.id,
        )
        return student


class GetStudentUseCase:
    def __init__(self, repository: StudentRepository) -> None:
        self.repository = repository

    def execute(self, query: GetStudentQuery):
        student = self.repository.get_by_id(query.student_id)
        if not student:
            raise StudentNotFoundError()
        _ensure_student_accessible(self.repository, student=student, current_user=query.current_user)
        return student


class UpdateStudentUseCase:
    def __init__(self, repository: StudentRepository) -> None:
        self.repository = repository

    def execute(self, command: UpdateStudentCommand):
        student = self.repository.get_by_id(command.student_id)
        if not student:
            raise StudentNotFoundError()
        _ensure_student_accessible(self.repository, student=student, current_user=command.current_user)

        new_code = command.changes.get("code")
        if new_code and new_code != student.code:
            if self.repository.code_exists(
                classroom_id=student.classroom_id,
                code=new_code,
                exclude_student_id=student.id,
            ):
                raise StudentCodeAlreadyExistsError()

        for field, value in command.changes.items():
            setattr(student, field, value)
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="update_student",
            entity_type="student",
            entity_id=student.id,
        )
        return student


class ListStudentSessionsUseCase:
    def __init__(self, repository: StudentRepository) -> None:
        self.repository = repository

    def execute(self, query: ListStudentSessionsQuery):
        student = self.repository.get_by_id(query.student_id)
        if not student:
            raise StudentNotFoundError()
        _ensure_student_accessible(self.repository, student=student, current_user=query.current_user)
        return self.repository.list_sessions(student.id)
