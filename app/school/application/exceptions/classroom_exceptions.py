from app.school.application.exceptions.school_exceptions import SchoolException


class ClassroomNotFoundError(SchoolException):
    def __init__(self, detail: str = "Classroom not found.") -> None:
        self.status_code = 404
        self.detail = detail


class DuplicateClassNameError(SchoolException):
    def __init__(self, detail: str = "A classroom with this name already exists for this teacher.") -> None:
        self.status_code = 409
        self.detail = detail


class ClassroomValidationError(SchoolException):
    def __init__(self, detail: str) -> None:
        self.status_code = 400
        self.detail = detail
