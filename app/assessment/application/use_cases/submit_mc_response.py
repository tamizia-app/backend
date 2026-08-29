from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.assemblers import MCResponseAssembler
from app.assessment.application.exceptions import (
    AttemptAlreadyCompletedError,
    ExerciseAttemptNotFoundError,
    InvalidMCOptionError,
    InvalidExerciseTypeError,
)
from app.assessment.application.ports.repositories import (
    ExerciseAttemptRepository,
    ExerciseScoreRepository,
    ExerciseRepository,
    AssessmentAttemptRepository,
    MCAnswerOptionRepository,
    MCQuestionRepository,
    MCResponseRepository,
    TemplateExerciseRepository,
)
from app.assessment.application.results import MCResponseResult
from app.assessment.application.exercise_score_service import persist_exercise_score
from app.assessment.domain.enums import AttemptStatus, ExerciseType, ExerciseAttemptStatus
from app.assessment.domain.response import MCResponse
from app.assessment.domain.technical_quality import valid_discrete_quality


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
        assessment_attempt_repo: AssessmentAttemptRepository,
        mc_response_repo: MCResponseRepository,
        mc_option_repo: MCAnswerOptionRepository,
        mc_question_repo: MCQuestionRepository,
        exercise_score_repo: ExerciseScoreRepository,
    ) -> None:
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._assessment_attempt_repo = assessment_attempt_repo
        self._mc_response_repo = mc_response_repo
        self._mc_option_repo = mc_option_repo
        self._mc_question_repo = mc_question_repo
        self._exercise_score_repo = exercise_score_repo

    def execute(self, command: SubmitMCResponseCommand) -> MCResponseResult:
        ea = self._exercise_attempt_repo.find_by_id(command.exercise_attempt_id)
        if not ea:
            raise ExerciseAttemptNotFoundError()

        attempt = self._assessment_attempt_repo.find_by_id(ea.assessment_attempt_id)
        if attempt and attempt.status == AttemptStatus.COMPLETED:
            raise AttemptAlreadyCompletedError("Completed attempts are immutable. Create a repeat attempt.")

        te = self._template_exercise_repo.find_by_id(ea.template_exercise_id)
        exercise = self._exercise_repo.find_by_id(te.exercise_id)
        if exercise.type != ExerciseType.MULTIPLE_CHOICE:
            raise InvalidExerciseTypeError(
                "Exercise is not MULTIPLE_CHOICE. Use the correct response endpoint."
            )

        question = self._mc_question_repo.find_by_exercise_id(exercise.id)
        option = self._mc_option_repo.find_by_id(command.selected_option_id)
        if not question or not option or option.mc_question_id != question.id:
            raise InvalidMCOptionError()
        is_correct = option.is_correct

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

        ea.status = ExerciseAttemptStatus.ANSWERED
        ea.submitted_at = now
        self._exercise_attempt_repo.update(ea)
        score = 100.0 if response.is_correct else 0.0
        persist_exercise_score(
            self._exercise_score_repo,
            exercise_attempt_id=ea.id,
            exercise_type=exercise.type,
            score=score,
            quality=valid_discrete_quality(score),
            scoring_components={"is_correct": response.is_correct, "formula": "100_if_correct_else_0"},
        )
        return MCResponseAssembler.to_result(response)
