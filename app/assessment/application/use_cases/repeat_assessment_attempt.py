from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.exceptions import AttemptNotFoundError
from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentRepository,
    ExerciseAttemptRepository,
    ExerciseRepository,
    TemplateExerciseRepository,
)
from app.assessment.application.results import AttemptResult, ExerciseAttemptResult
from app.assessment.application.assemblers import AttemptAssembler
from app.assessment.domain.attempt import AssessmentAttempt, ExerciseAttempt
from app.assessment.domain.enums import AttemptStatus, ExerciseAttemptStatus


@dataclass
class RepeatAssessmentAttemptCommand:
    attempt_id: UUID
    reason: str | None = None


class RepeatAssessmentAttemptUseCase:
    def __init__(
        self,
        attempt_repo: AssessmentAttemptRepository,
        exercise_attempt_repo: ExerciseAttemptRepository,
        template_exercise_repo: TemplateExerciseRepository,
        exercise_repo: ExerciseRepository,
        assessment_repo: AssessmentRepository,
    ) -> None:
        self._attempt_repo = attempt_repo
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._assessment_repo = assessment_repo

    def execute(self, command: RepeatAssessmentAttemptCommand) -> AttemptResult:
        original = self._attempt_repo.find_by_id(command.attempt_id)
        if not original:
            raise AttemptNotFoundError()

        if original.status.value != "COMPLETED":
            from app.assessment.application.exceptions import AssessmentException
            raise AssessmentException(
                status_code=400,
                detail="Can only repeat a COMPLETED attempt. Current status: " + original.status.value,
            )

        assessment = self._assessment_repo.find_by_id(original.assessment_id)
        if not assessment:
            from app.assessment.application.exceptions import AssessmentException
            raise AssessmentException(status_code=400, detail="Assessment not found.")

        now = datetime.now(timezone.utc)
        new_attempt = self._attempt_repo.create(
            AssessmentAttempt(
                id=UUID(int=0),
                assessment_id=original.assessment_id,
                student_id=original.student_id,
                status=AttemptStatus.IN_PROGRESS,
                started_at=now,
                completed_at=None,
                created_at=now,
                updated_at=now,
                repeated_from_attempt_id=original.id,
                repeat_reason=command.reason,
            )
        )

        template_exercises = self._template_exercise_repo.find_by_template_id(
            assessment.template_id
        )
        exercise_attempts = []
        for te in template_exercises:
            exercise_attempts.append(
                ExerciseAttempt(
                    id=UUID(int=0),
                    assessment_attempt_id=new_attempt.id,
                    template_exercise_id=te.id,
                    status=ExerciseAttemptStatus.PENDING,
                    started_at=None,
                    submitted_at=None,
                    created_at=now,
                    updated_at=now,
                )
            )
        saved = self._exercise_attempt_repo.create_many(exercise_attempts)

        exercise_attempt_results = [
            ExerciseAttemptResult(
                exercise_attempt_id=ea.id,
                template_exercise_id=ea.template_exercise_id,
                status=ea.status,
                started_at=ea.started_at,
                submitted_at=ea.submitted_at,
            )
            for ea in saved
        ]

        return AttemptAssembler.to_result(new_attempt, exercise_attempt_results)
