from app.school.application.exceptions.school_exceptions import SchoolException


class StudentNotFoundError(SchoolException):
    def __init__(self, detail: str = "Student not found.") -> None:
        self.status_code = 404
        self.detail = detail


class DuplicateStudentCodeError(SchoolException):
    def __init__(self, detail: str = "Student code already exists in this classroom.") -> None:
        self.status_code = 409
        self.detail = detail


class StudentValidationError(SchoolException):
    def __init__(self, detail: str) -> None:
        self.status_code = 400
        self.detail = detail


class StudentConsentNotFoundError(SchoolException):
    def __init__(self, detail: str = "Consent record not found.") -> None:
        self.status_code = 404
        self.detail = detail


class ConsentAlreadyExistsError(SchoolException):
    def __init__(self, detail: str = "Consent already exists for this student.") -> None:
        self.status_code = 409
        self.detail = detail


class ConsentAlreadyRevokedError(SchoolException):
    def __init__(self, detail: str = "Consent is already revoked.") -> None:
        self.status_code = 409
        self.detail = detail


class BlobStorageError(SchoolException):
    def __init__(self, detail: str = "File storage operation failed.") -> None:
        self.status_code = 500
        self.detail = detail
