from __future__ import annotations


class AssessmentSessionError(Exception):
    """Base exception for assessment session use cases."""


class SessionNotFoundError(AssessmentSessionError):
    pass


class SessionNotBelongsToTeacherError(AssessmentSessionError):
    pass


class StudentNotFoundError(AssessmentSessionError):
    pass


class StudentNotBelongsToTeacherError(AssessmentSessionError):
    pass


class ExerciseNotFoundError(AssessmentSessionError):
    pass


class TeacherProfileMissingError(AssessmentSessionError):
    pass


class InvalidSessionStateError(AssessmentSessionError):
    pass

