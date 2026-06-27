from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.assessment.domain.enums import AttemptStatus, ExerciseAttemptStatus


@dataclass
class AssessmentAttempt:
    id: UUID
    assessment_id: UUID
    student_id: UUID
    status: AttemptStatus
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class ExerciseAttempt:
    id: UUID
    assessment_attempt_id: UUID
    template_exercise_id: UUID
    status: ExerciseAttemptStatus
    started_at: datetime | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
