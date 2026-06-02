from __future__ import annotations


class ClassroomError(Exception):
    """Base exception for the classrooms module."""


class ClassroomNotFoundError(ClassroomError):
    pass


class ClassroomNotBelongsToTeacherError(ClassroomError):
    pass


class TeacherProfileMissingError(ClassroomError):
    pass

