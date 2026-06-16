from __future__ import annotations

from app.domain.enums import UserRole
from app.assessment.modules.assessment_sessions.domain.exceptions import (
    ExerciseNotFoundError,
    SessionNotBelongsToTeacherError,
    SessionNotFoundError,
    StudentNotBelongsToTeacherError,
    StudentNotFoundError,
    TeacherProfileMissingError,
)
from app.assessment.modules.assessment_sessions.domain.repositories import AssessmentSessionRepository


def teacher_profile_id_for(current_user):
    if not current_user.teacher_profile:
        raise TeacherProfileMissingError()
    return current_user.teacher_profile.id


def get_accessible_student(repository: AssessmentSessionRepository, *, student_id, current_user):
    student = repository.get_student(student_id)
    if not student:
        raise StudentNotFoundError()

    classroom = repository.get_student_classroom(student)
    if not classroom:
        raise StudentNotFoundError()
    if current_user.role != UserRole.ADMIN and classroom.teacher_profile_id != teacher_profile_id_for(current_user):
        raise StudentNotBelongsToTeacherError()
    return student


def get_active_exercise(repository: AssessmentSessionRepository, *, exercise_id):
    exercise = repository.get_exercise(exercise_id)
    if not exercise or not exercise.is_active:
        raise ExerciseNotFoundError()
    return exercise


def get_accessible_session(repository: AssessmentSessionRepository, *, session_id, current_user, with_details: bool = False):
    session = repository.get_session_with_details(session_id) if with_details else repository.get_session(session_id)
    if not session:
        raise SessionNotFoundError()

    try:
        get_accessible_student(repository, student_id=session.student_id, current_user=current_user)
    except StudentNotBelongsToTeacherError as exc:
        raise SessionNotBelongsToTeacherError() from exc
    except StudentNotFoundError as exc:
        raise SessionNotFoundError() from exc
    return session

