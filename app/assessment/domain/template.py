from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


DEFAULT_TEMPLATE_EXERCISE_POINTS = 2
VALID_TEMPLATE_EXERCISE_POINTS = frozenset({1, 2, 3})


def validate_template_exercise_points(points: int) -> None:
    if points not in VALID_TEMPLATE_EXERCISE_POINTS:
        raise ValueError("Template exercise points must be 1, 2, or 3.")


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
