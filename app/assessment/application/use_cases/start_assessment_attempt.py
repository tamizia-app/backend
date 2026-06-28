from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.assemblers import AttemptAssembler
from app.assessment.application.exceptions import (
    AssessmentNotFoundError,
    ConsentRequiredError,
    StudentNotInClassroomError,
)
from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentRepository,
    ExerciseAttemptRepository,
    TemplateExerciseRepository,
    TemplateRepository,
)
from app.assessment.application.results import AttemptResult, ExerciseAttemptResult
from app.assessment.domain.attempt import AssessmentAttempt, ExerciseAttempt
from app.assessment.domain.enums import AttemptStatus, ExerciseAttemptStatus
from app.school.application.ports.consent_repository import StudentConsentRepository
from app.school.application.ports.student_repository import StudentRepository


@dataclass
class StartAssessmentAttemptCommand:
    assessment_id: UUID
    student_id: UUID


class StartAssessmentAttemptUseCase:
    def __init__(
        self,
        assessment_repo: AssessmentRepository,
        attempt_repo: AssessmentAttemptRepository,
        exercise_attempt_repo: ExerciseAttemptRepository,
        template_exercise_repo: TemplateExerciseRepository,
        template_repo: TemplateRepository,
        student_repo: StudentRepository,
        consent_repo: StudentConsentRepository,
    ) -> None:
        self._assessment_repo = assessment_repo
        self._attempt_repo = attempt_repo
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._template_repo = template_repo
        self._student_repo = student_repo
        self._consent_repo = consent_repo

    def execute(self, command: StartAssessmentAttemptCommand) -> AttemptResult:
        assessment = self._assessment_repo.find_by_id(command.assessment_id)
        if not assessment:
            raise AssessmentNotFoundError()

        student = self._student_repo.find_by_id(command.student_id)
        if not student:
            raise StudentNotInClassroomError("Student not found.")

        if student.classroom_id != assessment.classroom_id:
            raise StudentNotInClassroomError()

        consent = self._consent_repo.find_by_student_id(command.student_id)
        if not consent or not consent.status:
            raise ConsentRequiredError()

        now = datetime.now(timezone.utc)
        attempt = self._attempt_repo.create(
            AssessmentAttempt(
                id=UUID(int=0),
                assessment_id=command.assessment_id,
                student_id=command.student_id,
                status=AttemptStatus.IN_PROGRESS,
                started_at=now,
                completed_at=None,
                created_at=now,
                updated_at=now,
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
                    assessment_attempt_id=attempt.id,
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

        return AttemptAssembler.to_result(attempt, exercise_attempt_results)
