class SchoolException(Exception):
    status_code: int = 500
    detail: str = "Internal school error"


class HomeroomTeacherNotFoundError(SchoolException):
    def __init__(self, detail: str = "HomeroomTeacher not found.") -> None:
        self.status_code = 404
        self.detail = detail


class UserNotFoundError(SchoolException):
    def __init__(self, detail: str = "User not found.") -> None:
        self.status_code = 404
        self.detail = detail


class ValidationError(SchoolException):
    def __init__(self, detail: str) -> None:
        self.status_code = 400
        self.detail = detail
