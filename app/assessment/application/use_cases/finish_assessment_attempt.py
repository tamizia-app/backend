from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.exceptions import (
    AttemptAlreadyCompletedError,
    AttemptNotFoundError,
)
from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentResultRepository,
    ExerciseAttemptRepository,
    ExerciseRepository,
    MCResponseRepository,
    OSResponseRepository,
    SpeakingResponseRepository,
    TemplateExerciseRepository,
    WritingResponseRepository,
)
from app.assessment.domain.enums import AttemptStatus, InterventionLevel
from app.assessment.domain.metrics import AssessmentResult


@dataclass
class FinishAssessmentAttemptCommand:
    attempt_id: UUID


class FinishAssessmentAttemptUseCase:
    def __init__(
        self,
        attempt_repo: AssessmentAttemptRepository,
        exercise_attempt_repo: ExerciseAttemptRepository,
        template_exercise_repo: TemplateExerciseRepository,
        exercise_repo: ExerciseRepository,
        mc_response_repo: MCResponseRepository,
        os_response_repo: OSResponseRepository,
        speaking_response_repo: SpeakingResponseRepository,
        writing_response_repo: WritingResponseRepository,
        result_repo: AssessmentResultRepository,
    ) -> None:
        self._attempt_repo = attempt_repo
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._mc_response_repo = mc_response_repo
        self._os_response_repo = os_response_repo
        self._speaking_response_repo = speaking_response_repo
        self._writing_response_repo = writing_response_repo
        self._result_repo = result_repo

    def execute(self, command: FinishAssessmentAttemptCommand) -> AssessmentResult:
        attempt = self._attempt_repo.find_by_id(command.attempt_id)
        if not attempt:
            raise AttemptNotFoundError()
        if attempt.status == AttemptStatus.COMPLETED:
            raise AttemptAlreadyCompletedError()

        exercise_attempts = self._exercise_attempt_repo.find_by_assessment_attempt_id(attempt.id)

        mc_correct = 0
        os_correct = 0
        speaking_done = 0
        writing_done = 0
        mc_total = 0
        os_total = 0
        speaking_total = 0
        writing_total = 0

        for ea in exercise_attempts:
            te = self._template_exercise_repo.find_by_id(ea.template_exercise_id)
            exercise = self._exercise_repo.find_by_id(te.exercise_id)
            etype = exercise.type

            if etype.value == "MULTIPLE_CHOICE":
                mc_total += 1
                resp = self._mc_response_repo.find_by_exercise_attempt_id(ea.id)
                if resp and resp.is_correct:
                    mc_correct += 1
            elif etype.value == "ORDER_SYLLABLES":
                os_total += 1
                resp = self._os_response_repo.find_by_exercise_attempt_id(ea.id)
                if resp and resp.is_correct:
                    os_correct += 1
            elif etype.value in ("READING_SPEAKING", "LISTENING_SPEAKING"):
                speaking_total += 1
                resp = self._speaking_response_repo.find_by_exercise_attempt_id(ea.id)
                if resp:
                    speaking_done += 1
            elif etype.value in ("READING_WRITING", "LISTENING_WRITING"):
                writing_total += 1
                resp = self._writing_response_repo.find_by_exercise_attempt_id(ea.id)
                if resp:
                    writing_done += 1

        max_score = (mc_total + os_total) * 10
        raw_score = (mc_correct + os_correct) * 10
        raw_score_with_speaking = raw_score + (speaking_done * 5) + (writing_done * 5)
        max_score_with_all = max_score + (speaking_total * 5) + (writing_total * 5)
        final_score = (raw_score_with_speaking / max_score_with_all * 100) if max_score_with_all > 0 else 0

        if final_score >= 80:
            level = InterventionLevel.LOW
        elif final_score >= 50:
            level = InterventionLevel.MEDIUM
        else:
            level = InterventionLevel.HIGH

        now = datetime.now(timezone.utc)
        attempt.status = AttemptStatus.COMPLETED
        attempt.completed_at = now
        self._attempt_repo.update(attempt)

        result = self._result_repo.create(
            AssessmentResult(
                id=UUID(int=0),
                assessment_attempt_id=attempt.id,
                final_score=round(final_score, 2),
                max_score=float(max_score_with_all),
                mc_correct_count=mc_correct,
                os_correct_count=os_correct,
                speaking_completed_count=speaking_done,
                writing_completed_count=writing_done,
                intervention_level=level,
                generated_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        return result
