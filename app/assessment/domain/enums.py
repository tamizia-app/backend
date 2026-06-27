from enum import StrEnum


class ExerciseType(StrEnum):
    ORDER_SYLLABLES = "ORDER_SYLLABLES"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    READING_SPEAKING = "READING_SPEAKING"
    READING_WRITING = "READING_WRITING"
    LISTENING_SPEAKING = "LISTENING_SPEAKING"
    LISTENING_WRITING = "LISTENING_WRITING"


class AssessmentStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class AttemptStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ExerciseAttemptStatus(StrEnum):
    PENDING = "PENDING"
    ANSWERED = "ANSWERED"
    EVALUATED = "EVALUATED"
    FAILED = "FAILED"


class InterventionLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
