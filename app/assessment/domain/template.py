from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class AssessmentTemplate:
    id: UUID
    name: str
    description: str | None
    version: int
    is_active: bool
    created_by_teacher_id: UUID | None
    created_at: datetime
    updated_at: datetime


@dataclass
class AssessmentTemplateExercise:
    id: UUID
    template_id: UUID
    exercise_id: UUID
    order_index: int
    points: int
    is_required: bool
    created_at: datetime
    updated_at: datetime
