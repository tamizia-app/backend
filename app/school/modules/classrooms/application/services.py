from __future__ import annotations

from app.domain.enums import UserRole
from app.school.modules.classrooms.application.commands.classroom_commands import CreateClassroomCommand, UpdateClassroomCommand
from app.school.modules.classrooms.application.queries.classroom_queries import GetClassroomQuery, ListClassroomsQuery
from app.school.modules.classrooms.domain.exceptions import (
    ClassroomNotBelongsToTeacherError,
    ClassroomNotFoundError,
    TeacherProfileMissingError,
)
from app.school.modules.classrooms.domain.repositories import ClassroomRepository


def _teacher_profile_id_for(current_user):
    if not current_user.teacher_profile:
        raise TeacherProfileMissingError()
    return current_user.teacher_profile.id


def _ensure_classroom_accessible(repository: ClassroomRepository, *, classroom_id, current_user):
    classroom = repository.get_by_id(classroom_id)
    if not classroom:
        raise ClassroomNotFoundError()
    if current_user.role != UserRole.ADMIN and classroom.teacher_profile_id != _teacher_profile_id_for(current_user):
        raise ClassroomNotBelongsToTeacherError()
    return classroom


class ListClassroomsUseCase:
    def __init__(self, repository: ClassroomRepository) -> None:
        self.repository = repository

    def execute(self, query: ListClassroomsQuery):
        if query.current_user.role == UserRole.ADMIN:
            return self.repository.list_all()
        return self.repository.list_by_teacher(_teacher_profile_id_for(query.current_user))


class CreateClassroomUseCase:
    def __init__(self, repository: ClassroomRepository) -> None:
        self.repository = repository

    def execute(self, command: CreateClassroomCommand):
        classroom = self.repository.create_classroom(
            teacher_profile_id=_teacher_profile_id_for(command.current_user),
            classroom_data=command.classroom_data,
        )
        self.repository.add(classroom)
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="create_classroom",
            entity_type="classroom",
            entity_id=classroom.id,
        )
        return classroom


class GetClassroomUseCase:
    def __init__(self, repository: ClassroomRepository) -> None:
        self.repository = repository

    def execute(self, query: GetClassroomQuery):
        return _ensure_classroom_accessible(
            self.repository,
            classroom_id=query.classroom_id,
            current_user=query.current_user,
        )


class UpdateClassroomUseCase:
    def __init__(self, repository: ClassroomRepository) -> None:
        self.repository = repository

    def execute(self, command: UpdateClassroomCommand):
        classroom = _ensure_classroom_accessible(
            self.repository,
            classroom_id=command.classroom_id,
            current_user=command.current_user,
        )
        for field, value in command.changes.items():
            setattr(classroom, field, value)
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="update_classroom",
            entity_type="classroom",
            entity_id=classroom.id,
        )
        return classroom
