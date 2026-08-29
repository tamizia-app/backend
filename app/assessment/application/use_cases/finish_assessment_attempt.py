from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.exceptions import (
    AttemptAlreadyCompletedError,
    AttemptNotEvaluableError,
    AttemptNotFoundError,
)
from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentResultRepository,
    ExerciseAttemptRepository,
    ExerciseRepository,
    ExerciseScoreRepository,
    TemplateExerciseRepository,
)
from app.assessment.domain.enums import AttemptStatus, ExerciseType, InterventionLevel
from app.assessment.domain.metrics import AssessmentResult, ExerciseScore


@dataclass
class FinishAssessmentAttemptCommand:
    attempt_id: UUID


class FinishAssessmentAttemptUseCase:
    """Finalize an attempt exclusively from canonical per-exercise scores."""

    def __init__(
        self,
        attempt_repo: AssessmentAttemptRepository,
        exercise_attempt_repo: ExerciseAttemptRepository,
        template_exercise_repo: TemplateExerciseRepository,
        exercise_repo: ExerciseRepository,
        exercise_score_repo: ExerciseScoreRepository,
        result_repo: AssessmentResultRepository,
    ) -> None:
        self._attempt_repo = attempt_repo
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._exercise_score_repo = exercise_score_repo
        self._result_repo = result_repo

    def execute(self, command: FinishAssessmentAttemptCommand) -> AssessmentResult:
        attempt = self._attempt_repo.find_by_id(command.attempt_id)
        if not attempt:
            raise AttemptNotFoundError()
        if attempt.status == AttemptStatus.COMPLETED:
            raise AttemptAlreadyCompletedError()

        exercise_attempts = self._exercise_attempt_repo.find_by_assessment_attempt_id(attempt.id)
        canonical = {
            score.exercise_attempt_id: score
            for score in self._exercise_score_repo.find_by_assessment_attempt_id(attempt.id)
        }
        rows = []
        blocking: list[dict] = []
        for exercise_attempt in exercise_attempts:
            template_exercise = self._template_exercise_repo.find_by_id(
                exercise_attempt.template_exercise_id
            )
            exercise = self._exercise_repo.find_by_id(template_exercise.exercise_id)
            score = canonical.get(exercise_attempt.id)
            rows.append((exercise_attempt, template_exercise, exercise, score))
            if template_exercise.is_required and (
                score is None or not score.score_eligible or score.score is None
            ):
                blocking.append(
                    {
                        "exercise_attempt_id": str(exercise_attempt.id),
                        "exercise_type": exercise.type.value,
                        "technical_status": score.technical_status.value if score else "INVALID",
                        "quality_reasons": score.quality_reasons if score else ["MISSING_CANONICAL_SCORE"],
                    }
                )

        if blocking:
            raise AttemptNotEvaluableError(
                "Required exercises are not technically score-eligible; repeat or review the sample: "
                + str(blocking)
            )

        included = [score for *_, score in rows if score and score.score_eligible and score.score is not None]
        if not included:
            raise AttemptNotEvaluableError("Attempt has no technically valid, score-eligible exercises.")

        final_score = sum(score.score for score in included if score.score is not None) / len(included)
        review_required_count = sum(score.manual_review_required for score in included)
        writing_review_count = sum(
            score.manual_review_required
            for score in included
            if score.exercise_type in (ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING)
        )
        level = self._determine_intervention_level(
            final_score, review_required_count, writing_review_count
        )

        speaking_scores = [
            score.score
            for score in included
            if score.exercise_type in (ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING)
            and score.score is not None
        ]
        writing_scores = [
            score.score
            for score in included
            if score.exercise_type in (ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING)
            and score.score is not None
        ]
        snapshot = [self._snapshot_row(*row) for row in rows]
        now = datetime.now(timezone.utc)
        attempt.status = AttemptStatus.COMPLETED
        attempt.completed_at = now
        self._attempt_repo.update(attempt)

        return self._result_repo.create(
            AssessmentResult(
                id=UUID(int=0),
                assessment_attempt_id=attempt.id,
                final_score=round(final_score, 2),
                max_score=100.0,
                mc_correct_count=sum(
                    score.scoring_components.get("is_correct") is True
                    for score in included
                    if score.exercise_type == ExerciseType.MULTIPLE_CHOICE
                ),
                os_correct_count=sum(
                    score.scoring_components.get("is_correct") is True
                    for score in included
                    if score.exercise_type == ExerciseType.ORDER_SYLLABLES
                ),
                speaking_completed_count=sum(
                    score.exercise_type in (ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING)
                    for score in included
                ),
                writing_completed_count=sum(
                    score.exercise_type in (ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING)
                    for score in included
                ),
                intervention_level=level,
                generated_at=now,
                created_at=now,
                updated_at=now,
                speaking_average_score=(sum(speaking_scores) / len(speaking_scores) if speaking_scores else None),
                speaking_review_required_count=sum(
                    score.manual_review_required
                    for score in included
                    if score.exercise_type in (ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING)
                ),
                total_exercises=len(rows),
                evaluated_exercises=len(included),
                pending_exercises=len(rows) - len(included),
                writing_average_score=(sum(writing_scores) / len(writing_scores) if writing_scores else None),
                writing_review_required_count=writing_review_count,
                score_denominator=len(included),
                scoring_snapshot_json=snapshot,
            )
        )

    @staticmethod
    def _snapshot_row(exercise_attempt, template_exercise, exercise, score: ExerciseScore | None) -> dict:
        included = bool(score and score.score_eligible and score.score is not None)
        return {
            "exercise_attempt_id": str(exercise_attempt.id),
            "exercise_id": str(exercise.id),
            "template_exercise_id": str(template_exercise.id),
            "exercise_type": exercise.type.value,
            "order_index": template_exercise.order_index,
            "is_required": template_exercise.is_required,
            "score": score.score if score else None,
            "score_eligible": score.score_eligible if score else False,
            "included": included,
            "exclusion_reason": None if included else "NOT_SCORE_ELIGIBLE",
            "technical_status": score.technical_status.value if score else "INVALID",
            "manual_review_required": score.manual_review_required if score else True,
            "quality_reasons": score.quality_reasons if score else ["MISSING_CANONICAL_SCORE"],
            "review": {
                "required": score.manual_review_required if score else True,
                "reasons": score.quality_reasons if score else ["MISSING_CANONICAL_SCORE"],
            },
            "scoring_components": score.scoring_components if score else {},
        }

    @staticmethod
    def _determine_intervention_level(
        final_score: float,
        review_required_count: int,
        writing_review_required_count: int = 0,
    ) -> InterventionLevel:
        if final_score >= 80:
            if review_required_count > 0:
                return InterventionLevel.MEDIUM
            return InterventionLevel.LOW
        if final_score >= 50:
            if writing_review_required_count > 0 and final_score < 70:
                return InterventionLevel.HIGH
            return InterventionLevel.MEDIUM
        return InterventionLevel.HIGH
