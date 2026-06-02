from __future__ import annotations


class StudentError(Exception):
    """Base exception for the students module."""


class StudentNotFoundError(StudentError):
    pass


class StudentNotBelongsToTeacherError(StudentError):
    pass


class StudentCodeAlreadyExistsError(StudentError):
    pass


class ClassroomNotFoundError(StudentError):
    pass


class TeacherProfileMissingError(StudentError):
    pass

