from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.assemblers import OSResponseAssembler
from app.assessment.application.exceptions import (
    ExerciseAttemptNotFoundError,
    InvalidExerciseTypeError,
)
from app.assessment.application.ports.repositories import (
    ExerciseAttemptRepository,
    ExerciseRepository,
    OSAnswerRepository,
    OSQuestionRepository,
    OSResponseRepository,
    TemplateExerciseRepository,
)
from app.assessment.application.results import OSResponseResult
from app.assessment.domain.enums import ExerciseType, ExerciseAttemptStatus
from app.assessment.domain.response import OSResponse


@dataclass
class SubmitOSResponseCommand:
    exercise_attempt_id: UUID
    selected_syllables: list[str]
    formed_word: str | None


class SubmitOSResponseUseCase:
    def __init__(
        self,
        exercise_attempt_repo: ExerciseAttemptRepository,
        template_exercise_repo: TemplateExerciseRepository,
        exercise_repo: ExerciseRepository,
        os_response_repo: OSResponseRepository,
        os_question_repo: OSQuestionRepository,
        os_answer_repo: OSAnswerRepository,
    ) -> None:
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._os_response_repo = os_response_repo
        self._os_question_repo = os_question_repo
        self._os_answer_repo = os_answer_repo

    def execute(self, command: SubmitOSResponseCommand) -> OSResponseResult:
        ea = self._exercise_attempt_repo.find_by_id(command.exercise_attempt_id)
        if not ea:
            raise ExerciseAttemptNotFoundError()

        te = self._template_exercise_repo.find_by_id(ea.template_exercise_id)
        exercise = self._exercise_repo.find_by_id(te.exercise_id)
        if exercise.type != ExerciseType.ORDER_SYLLABLES:
            raise InvalidExerciseTypeError(
                "Exercise is not ORDER_SYLLABLES. Use the correct response endpoint."
            )

        os_q = self._os_question_repo.find_by_exercise_id(exercise.id)
        is_correct: bool | None = None
        if os_q:
            expected = self._os_answer_repo.find_by_question_id(os_q.id)
            if expected:
                if command.formed_word:
                    is_correct = command.formed_word.strip().lower() == expected.correct_word.strip().lower()

        now = datetime.now(timezone.utc)
        existing = self._os_response_repo.find_by_exercise_attempt_id(command.exercise_attempt_id)
        if existing:
            response = self._os_response_repo.update(
                OSResponse(
                    id=existing.id,
                    exercise_attempt_id=command.exercise_attempt_id,
                    selected_syllables_json=command.selected_syllables,
                    formed_word=command.formed_word,
                    is_correct=is_correct,
                    created_at=existing.created_at,
                    updated_at=now,
                )
            )
        else:
            response = self._os_response_repo.create(
                OSResponse(
                    id=UUID(int=0),
                    exercise_attempt_id=command.exercise_attempt_id,
                    selected_syllables_json=command.selected_syllables,
                    formed_word=command.formed_word,
                    is_correct=is_correct,
                    created_at=now,
                    updated_at=now,
                )
            )

        ea.status = ExerciseAttemptStatus.ANSWERED
        ea.submitted_at = now
        self._exercise_attempt_repo.update(ea)
        return OSResponseAssembler.to_result(response)
