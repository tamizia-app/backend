class IAMException(Exception):
    status_code: int = 500
    detail: str = "Internal IAM error"


class ValidationException(IAMException):
    def __init__(self, detail: str) -> None:
        self.status_code = 400
        self.detail = detail


class InvalidCredentialsException(IAMException):
    def __init__(self, detail: str = "Invalid credentials.") -> None:
        self.status_code = 401
        self.detail = detail


class InactiveUserException(IAMException):
    def __init__(self, detail: str = "Inactive user.") -> None:
        self.status_code = 403
        self.detail = detail


class NotFoundException(IAMException):
    def __init__(self, detail: str = "Resource not found.") -> None:
        self.status_code = 404
        self.detail = detail


class AlreadyExistsException(IAMException):
    def __init__(self, detail: str = "Resource already exists.") -> None:
        self.status_code = 409
        self.detail = detail
