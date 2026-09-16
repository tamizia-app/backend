from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.exceptions import (
    AttemptAlreadyCompletedError,
    AttemptNotEvaluableError,
    AttemptNotFoundError,
    InvalidTemplateExercisePointsError,
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
from app.assessment.domain.technical_quality import SCORING_VERSION_PHASE2_V1
from app.assessment.domain.template import validate_template_exercise_points


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
            current_score = self._current_score(score)
            rows.append((exercise_attempt, template_exercise, exercise, score))
            try:
                validate_template_exercise_points(template_exercise.points)
            except ValueError as exc:
                raise InvalidTemplateExercisePointsError(
                    f"{exc} template_exercise_id={template_exercise.id}; "
                    "legacy templates must be corrected before finishing."
                )
            if template_exercise.is_required and (
                score is None or not score.score_eligible or current_score is None
            ):
                blocking.append(
                    {
                        "exercise_attempt_id": str(exercise_attempt.id),
                        "template_exercise_id": str(template_exercise.id),
                        "exercise_id": str(exercise.id),
                        "exercise_type": exercise.type.value,
                        "order_index": template_exercise.order_index,
                        "technical_status": score.technical_status.value if score else "INVALID",
                        "score_eligible": score.score_eligible if score else False,
                        "quality_reasons": score.quality_reasons if score else ["MISSING_CANONICAL_SCORE"],
                        "manual_review_required": score.manual_review_required if score else True,
                    }
                )

        if blocking:
            raise AttemptNotEvaluableError(
                {
                    "code": "ASSESSMENT_NOT_INTERPRETABLE",
                    "message": (
                        "La evaluación no cuenta con evidencia suficiente para generar "
                        "un resultado global interpretable."
                    ),
                    "reason": "required_exercise_not_eligible",
                    "scoring_version": SCORING_VERSION_PHASE2_V1,
                    "blocking_required_exercises": blocking,
                    "recommendation": (
                        "Aplicar una forma equivalente de la batería en lugar de repetir "
                        "exactamente la misma plantilla."
                    ),
                }
            )

        included_rows = [
            (exercise_attempt, template_exercise, exercise, score)
            for exercise_attempt, template_exercise, exercise, score in rows
            if score and score.score_eligible and self._current_score(score) is not None
        ]
        included = [score for *_, score in included_rows]
        if not included_rows:
            raise AttemptNotEvaluableError("Attempt has no technically valid, score-eligible exercises.")

        included_weight_sum = sum(template_exercise.points for _, template_exercise, _, _ in included_rows)
        total_template_weight_sum = sum(template_exercise.points for _, template_exercise, _, _ in rows)
        final_score = (
            sum(self._current_score(score) * template_exercise.points for _, template_exercise, _, score in included_rows)
            / included_weight_sum
        )
        final_score = max(0.0, min(100.0, final_score))
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
            self._current_score(score)
            for score in included
            if score.exercise_type in (ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING)
            and self._current_score(score) is not None
        ]
        writing_scores = [
            self._current_score(score)
            for score in included
            if score.exercise_type in (ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING)
            and self._current_score(score) is not None
        ]
        included_exercise_count = len(included_rows)
        total_exercise_count = len(rows)
        coverage_weight_percentage = (
            round((included_weight_sum / total_template_weight_sum) * 100, 2)
            if total_template_weight_sum
            else 0.0
        )
        snapshot = [
            self._snapshot_row(
                *row,
                included_weight_sum=included_weight_sum,
                total_template_weight_sum=total_template_weight_sum,
                included_exercise_count=included_exercise_count,
                total_exercise_count=total_exercise_count,
                coverage_weight_percentage=coverage_weight_percentage,
            )
            for row in rows
        ]
        now = datetime.now(timezone.utc)
        attempt.status = AttemptStatus.COMPLETED
        attempt.completed_at = now
        self._attempt_repo.update(attempt)

        rounded_final_score = round(final_score, 2)
        return self._result_repo.create(
            AssessmentResult(
                id=UUID(int=0),
                assessment_attempt_id=attempt.id,
                final_score=rounded_final_score,
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
                score_denominator=included_weight_sum,
                scoring_snapshot_json=snapshot,
                original_final_score=rounded_final_score,
                current_final_score=rounded_final_score,
                original_scoring_snapshot_json=snapshot,
                current_scoring_snapshot_json=snapshot,
            )
        )

    @staticmethod
    def _snapshot_row(
        exercise_attempt,
        template_exercise,
        exercise,
        score: ExerciseScore | None,
        *,
        included_weight_sum: int,
        total_template_weight_sum: int,
        included_exercise_count: int,
        total_exercise_count: int,
        coverage_weight_percentage: float,
    ) -> dict:
        current_score = FinishAssessmentAttemptUseCase._current_score(score)
        included = bool(score and score.score_eligible and current_score is not None)
        exclusion_reason = None
        if not included:
            if score is None:
                exclusion_reason = "MISSING_CANONICAL_SCORE"
            elif not score.score_eligible:
                exclusion_reason = "NOT_SCORE_ELIGIBLE"
            else:
                exclusion_reason = "MISSING_SCORE"
        effective_weight_percentage = (
            round((template_exercise.points / included_weight_sum) * 100, 2)
            if included and included_weight_sum
            else None
        )
        return {
            "scoring_version": SCORING_VERSION_PHASE2_V1,
            "exercise_attempt_id": str(exercise_attempt.id),
            "exercise_id": str(exercise.id),
            "template_exercise_id": str(template_exercise.id),
            "exercise_type": exercise.type.value,
            "order_index": template_exercise.order_index,
            "is_required": template_exercise.is_required,
            "points": template_exercise.points,
            "score": current_score if score else None,
            "original_score": score.original_score if score else None,
            "current_score": current_score if score else None,
            "score_eligible": score.score_eligible if score else False,
            "included": included,
            "exclusion_reason": exclusion_reason,
            "technical_status": score.technical_status.value if score else "INVALID",
            "manual_review_required": score.manual_review_required if score else True,
            "quality_reasons": score.quality_reasons if score else ["MISSING_CANONICAL_SCORE"],
            "review": {
                "required": score.manual_review_required if score else True,
                "reasons": score.quality_reasons if score else ["MISSING_CANONICAL_SCORE"],
            },
            "scoring_components": score.current_scoring_components or score.scoring_components if score else {},
            "original_scoring_components": score.original_scoring_components if score else {},
            "current_scoring_components": score.current_scoring_components or score.scoring_components if score else {},
            "manual_adjustment_applied": score.manual_adjustment_applied if score else False,
            "teacher_observation": score.teacher_observation if score else None,
            "adjusted_by_teacher_id": str(score.adjusted_by_teacher_id) if score and score.adjusted_by_teacher_id else None,
            "adjusted_at": score.adjusted_at.isoformat() if score and score.adjusted_at else None,
            "weighted_contribution": current_score * template_exercise.points if included and score else None,
            "effective_weight": template_exercise.points if included else None,
            "effective_weight_percentage": effective_weight_percentage,
            "final_scoring_formula": "weighted_mean_by_template_exercise_points",
            "included_weight_sum": included_weight_sum,
            "total_template_weight_sum": total_template_weight_sum,
            "included_exercise_count": included_exercise_count,
            "total_exercise_count": total_exercise_count,
            "invalid_or_excluded_exercise_count": total_exercise_count - included_exercise_count,
            "coverage_weight_percentage": coverage_weight_percentage,
            "score_denominator_type": "included_weight_sum",
            "score_denominator_deprecated": True,
            "intervention_level_status": "provisional",
        }

    @staticmethod
    def _current_score(score: ExerciseScore | None) -> float | None:
        if score is None:
            return None
        return score.current_score if score.current_score is not None else score.score

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
