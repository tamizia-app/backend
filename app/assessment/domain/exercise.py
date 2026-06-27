from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.assessment.domain.enums import ExerciseType


@dataclass
class AssessmentExercise:
    id: UUID
    type: ExerciseType
    title: str
    instructions: str | None
    stimulus_type: str | None
    response_type: str | None
    difficulty_level: int | None
    is_active: bool
    created_by_teacher_id: UUID | None
    created_at: datetime
    updated_at: datetime
