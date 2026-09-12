from dataclasses import dataclass
from uuid import UUID

from app.assessment.application.exceptions import (
    InvalidTemplateExercisePointsError,
    TemplateExerciseNotFoundError,
    TemplateNotFoundError,
)
from app.assessment.application.ports.repositories import TemplateExerciseRepository, TemplateRepository
from app.assessment.domain.template import AssessmentTemplateExercise, validate_template_exercise_points


@dataclass
class UpdateTemplateExercisePointsCommand:
    template_id: UUID
    template_exercise_id: UUID
    teacher_id: UUID
    points: int


class UpdateTemplateExercisePointsUseCase:
    def __init__(
        self,
        template_repo: TemplateRepository,
        template_exercise_repo: TemplateExerciseRepository,
    ) -> None:
        self._template_repo = template_repo
        self._template_exercise_repo = template_exercise_repo

    def execute(self, command: UpdateTemplateExercisePointsCommand) -> AssessmentTemplateExercise:
        template = self._template_repo.find_owned_by_id(command.template_id, command.teacher_id)
        if not template:
            raise TemplateNotFoundError()

        template_exercise = self._template_exercise_repo.find_by_id(command.template_exercise_id)
        if not template_exercise or template_exercise.template_id != command.template_id:
            raise TemplateExerciseNotFoundError()

        try:
            validate_template_exercise_points(command.points)
        except ValueError as exc:
            raise InvalidTemplateExercisePointsError(str(exc))

        return self._template_exercise_repo.update_points(
            command.template_exercise_id,
            command.points,
        )
