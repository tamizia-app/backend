from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.exceptions import ExerciseNotFoundError, TemplateNotFoundError
from app.assessment.application.ports.repositories import ExerciseRepository, TemplateExerciseRepository, TemplateRepository
from app.assessment.domain.template import AssessmentTemplateExercise


@dataclass
class AttachExerciseCommand:
    template_id: UUID
    exercise_id: UUID
    order_index: int
    points: int
    is_required: bool


class AttachExerciseToTemplateUseCase:
    def __init__(
        self,
        template_repo: TemplateRepository,
        exercise_repo: ExerciseRepository,
        template_exercise_repo: TemplateExerciseRepository,
    ) -> None:
        self._template_repo = template_repo
        self._exercise_repo = exercise_repo
        self._template_exercise_repo = template_exercise_repo

    def execute(self, command: AttachExerciseCommand) -> None:
        template = self._template_repo.find_by_id(command.template_id)
        if not template:
            raise TemplateNotFoundError()

        exercise = self._exercise_repo.find_by_id(command.exercise_id)
        if not exercise:
            raise ExerciseNotFoundError()

        now = datetime.now(timezone.utc)
        self._template_exercise_repo.create(
            AssessmentTemplateExercise(
                id=UUID(int=0),
                template_id=command.template_id,
                exercise_id=command.exercise_id,
                order_index=command.order_index,
                points=command.points,
                is_required=command.is_required,
                created_at=now,
                updated_at=now,
            )
        )
