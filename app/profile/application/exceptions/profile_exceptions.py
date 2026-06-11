class ProfileException(Exception):
    status_code: int = 500
    detail: str = "Internal profile error"


class TeacherNotFoundError(ProfileException):
    def __init__(self, detail: str = "Teacher not found.") -> None:
        self.status_code = 404
        self.detail = detail


class UserNotFoundError(ProfileException):
    def __init__(self, detail: str = "User not found.") -> None:
        self.status_code = 404
        self.detail = detail


class ValidationError(ProfileException):
    def __init__(self, detail: str) -> None:
        self.status_code = 400
        self.detail = detail
