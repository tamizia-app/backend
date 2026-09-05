from dataclasses import dataclass
from uuid import UUID

from app.assessment.application.ports.repositories import TemplateExerciseRepository


@dataclass
class InvalidTemplatePointsItem:
    template_id: UUID
    template_name: str
    template_version: int
    is_active: bool
    template_exercise_id: UUID
    exercise_id: UUID
    exercise_type: str
    order_index: int
    current_points: int
    reason: str = "points_out_of_phase2_range"


@dataclass
class ListInvalidTemplatePointsQuery:
    teacher_id: UUID


class ListInvalidTemplatePointsUseCase:
    def __init__(self, template_exercise_repo: TemplateExerciseRepository) -> None:
        self._template_exercise_repo = template_exercise_repo

    def execute(self, query: ListInvalidTemplatePointsQuery) -> list[InvalidTemplatePointsItem]:
        rows = self._template_exercise_repo.find_invalid_points_by_teacher_id(query.teacher_id)
        return [InvalidTemplatePointsItem(**row) for row in rows]
