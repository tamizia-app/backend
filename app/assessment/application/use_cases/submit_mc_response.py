from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.assemblers import MCResponseAssembler
from app.assessment.application.exceptions import (
    ExerciseAttemptNotFoundError,
    InvalidExerciseTypeError,
)
from app.assessment.application.ports.repositories import (
    ExerciseAttemptRepository,
    ExerciseRepository,
    MCAnswerOptionRepository,
    MCResponseRepository,
    TemplateExerciseRepository,
)
from app.assessment.application.results import MCResponseResult
from app.assessment.domain.enums import ExerciseType, ExerciseAttemptStatus
from app.assessment.domain.response import MCResponse


@dataclass
class SubmitMCResponseCommand:
    exercise_attempt_id: UUID
    selected_option_id: UUID


class SubmitMCResponseUseCase:
    def __init__(
        self,
        exercise_attempt_repo: ExerciseAttemptRepository,
        template_exercise_repo: TemplateExerciseRepository,
        exercise_repo: ExerciseRepository,
        mc_response_repo: MCResponseRepository,
        mc_option_repo: MCAnswerOptionRepository,
    ) -> None:
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._mc_response_repo = mc_response_repo
        self._mc_option_repo = mc_option_repo

    def execute(self, command: SubmitMCResponseCommand) -> MCResponseResult:
        ea = self._exercise_attempt_repo.find_by_id(command.exercise_attempt_id)
        if not ea:
            raise ExerciseAttemptNotFoundError()

        te = self._template_exercise_repo.find_by_id(ea.template_exercise_id)
        exercise = self._exercise_repo.find_by_id(te.exercise_id)
        if exercise.type != ExerciseType.MULTIPLE_CHOICE:
            raise InvalidExerciseTypeError(
                "Exercise is not MULTIPLE_CHOICE. Use the correct response endpoint."
            )

        option = self._mc_option_repo.find_by_id(command.selected_option_id)
        is_correct = option.is_correct if option else None

        now = datetime.now(timezone.utc)
        existing = self._mc_response_repo.find_by_exercise_attempt_id(command.exercise_attempt_id)
        if existing:
            response = self._mc_response_repo.update(
                MCResponse(
                    id=existing.id,
                    exercise_attempt_id=command.exercise_attempt_id,
                    selected_option_id=command.selected_option_id,
                    is_correct=is_correct,
                    created_at=existing.created_at,
                    updated_at=now,
                )
            )
        else:
            response = self._mc_response_repo.create(
                MCResponse(
                    id=UUID(int=0),
                    exercise_attempt_id=command.exercise_attempt_id,
                    selected_option_id=command.selected_option_id,
                    is_correct=is_correct,
                    created_at=now,
                    updated_at=now,
                )
            )

        self._exercise_attempt_repo.update(ea)
        return MCResponseAssembler.to_result(response)
