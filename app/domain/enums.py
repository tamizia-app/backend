from enum import StrEnum


class UserRole(StrEnum):
    TEACHER = "teacher"
    ADMIN = "admin"


class ExerciseType(StrEnum):
    WRITING = "writing"
    READING = "reading"
    COMBINED = "combined"


class SessionStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskFlag(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH_REVIEW = "HIGH_REVIEW"

