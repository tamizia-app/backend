class AssessmentException(Exception):
    status_code: int = 500
    detail: str = "Internal assessment error"


class TemplateNotFoundError(AssessmentException):
    def __init__(self, detail: str = "Template not found.") -> None:
        self.status_code = 404
        self.detail = detail


class ExerciseNotFoundError(AssessmentException):
    def __init__(self, detail: str = "Exercise not found.") -> None:
        self.status_code = 404
        self.detail = detail


class AssessmentNotFoundError(AssessmentException):
    def __init__(self, detail: str = "Assessment not found.") -> None:
        self.status_code = 404
        self.detail = detail


class AttemptNotFoundError(AssessmentException):
    def __init__(self, detail: str = "Assessment attempt not found.") -> None:
        self.status_code = 404
        self.detail = detail


class ExerciseAttemptNotFoundError(AssessmentException):
    def __init__(self, detail: str = "Exercise attempt not found.") -> None:
        self.status_code = 404
        self.detail = detail


class StudentNotInClassroomError(AssessmentException):
    def __init__(self, detail: str = "Student does not belong to this classroom.") -> None:
        self.status_code = 400
        self.detail = detail


class TeacherNotOwnerError(AssessmentException):
    def __init__(self, detail: str = "Teacher does not own this classroom.") -> None:
        self.status_code = 403
        self.detail = detail


class InvalidExerciseTypeError(AssessmentException):
    def __init__(self, detail: str = "Invalid exercise type for this response.") -> None:
        self.status_code = 400
        self.detail = detail


class ResponseAlreadyExistsError(AssessmentException):
    def __init__(self, detail: str = "A response already exists for this exercise attempt.") -> None:
        self.status_code = 409
        self.detail = detail


class ConsentRequiredError(AssessmentException):
    def __init__(self, detail: str = "Student does not have active consent.") -> None:
        self.status_code = 403
        self.detail = detail


class AttemptAlreadyCompletedError(AssessmentException):
    def __init__(self, detail: str = "Attempt is already completed.") -> None:
        self.status_code = 400
        self.detail = detail


class StorageError(AssessmentException):
    def __init__(self, detail: str = "File storage operation failed.") -> None:
        self.status_code = 500
        self.detail = detail
