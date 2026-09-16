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
from app.assessment.domain.enums import AttemptStatus, ExerciseType, InterventionLevel, TechnicalStatus
from app.assessment.domain.metrics import AssessmentResult, ExerciseScore
from app.assessment.domain.technical_quality import SCORING_VERSION_PHASE2_V1
from app.assessment.domain.template import validate_template_exercise_points


@dataclass
class FinishAssessmentAttemptCommand:
    attempt_id: UUID


class FinishAssessmentAttemptUseCase:
    """Finalize an attempt exclusively from canonical per-exercise scores."""

    MINIMUM_SCORE_COVERAGE_PERCENTAGE = 70.0

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
        included_rows = [
            (exercise_attempt, template_exercise, exercise, score)
            for exercise_attempt, template_exercise, exercise, score in rows
            if self._is_included_score(score)
        ]
        included = [score for *_, score in included_rows]

        included_weight_sum = sum(template_exercise.points for _, template_exercise, _, _ in included_rows)
        total_template_weight_sum = sum(template_exercise.points for _, template_exercise, _, _ in rows)
        coverage_weight_percentage = (
            round((included_weight_sum / total_template_weight_sum) * 100, 2)
            if total_template_weight_sum
            else 0.0
        )
        self._raise_if_not_interpretable(
            rows=rows,
            included_rows=included_rows,
            included_weight_sum=included_weight_sum,
            total_template_weight_sum=total_template_weight_sum,
            coverage_weight_percentage=coverage_weight_percentage,
        )
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
        warning_metadata = self._warning_metadata(rows)
        snapshot = [
            self._snapshot_row(
                *row,
                included_weight_sum=included_weight_sum,
                total_template_weight_sum=total_template_weight_sum,
                included_exercise_count=included_exercise_count,
                total_exercise_count=total_exercise_count,
                coverage_weight_percentage=coverage_weight_percentage,
                partial_exercise_count=warning_metadata["partial_exercise_count"],
                invalid_exercise_count=warning_metadata["invalid_exercise_count"],
                result_status=warning_metadata["result_status"],
                has_warnings=warning_metadata["has_warnings"],
                warning_reasons=warning_metadata["warning_reasons"],
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
        partial_exercise_count: int,
        invalid_exercise_count: int,
        result_status: str,
        has_warnings: bool,
        warning_reasons: list[str],
    ) -> dict:
        current_score = FinishAssessmentAttemptUseCase._current_score(score)
        included = FinishAssessmentAttemptUseCase._is_included_score(score)
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
        current_components = FinishAssessmentAttemptUseCase._clean_scoring_components(
            score.current_scoring_components or score.scoring_components if score else {}
        )
        original_components = (
            FinishAssessmentAttemptUseCase._original_scoring_components(score)
            if score
            else {}
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
            "scoring_components": current_components,
            "original_scoring_components": original_components,
            "current_scoring_components": current_components,
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
            "partial_exercise_count": partial_exercise_count,
            "invalid_exercise_count": invalid_exercise_count,
            "coverage_weight_percentage": coverage_weight_percentage,
            "result_status": result_status,
            "has_warnings": has_warnings,
            "warning_reasons": warning_reasons,
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
    def _is_included_score(score: ExerciseScore | None) -> bool:
        if score is None or FinishAssessmentAttemptUseCase._current_score(score) is None:
            return False
        return score.score_eligible or score.technical_status == TechnicalStatus.PARTIAL

    @classmethod
    def _raise_if_not_interpretable(
        cls,
        *,
        rows: list[tuple],
        included_rows: list[tuple],
        included_weight_sum: int,
        total_template_weight_sum: int,
        coverage_weight_percentage: float,
    ) -> None:
        reason = None
        if coverage_weight_percentage < cls.MINIMUM_SCORE_COVERAGE_PERCENTAGE:
            reason = "insufficient_score_coverage"
        elif cls._domain_expected(rows, (ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING)) and not cls._domain_included(
            included_rows, (ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING)
        ):
            reason = "no_speaking_evidence"
        elif cls._domain_expected(rows, (ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING)) and not cls._domain_included(
            included_rows, (ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING)
        ):
            reason = "no_writing_evidence"

        if not reason:
            return

        raise AttemptNotEvaluableError(
            {
                "code": "ASSESSMENT_NOT_INTERPRETABLE",
                "message": (
                    "La evaluación no cuenta con evidencia suficiente para generar "
                    "un resultado global interpretable."
                ),
                "reason": reason,
                "scoring_version": SCORING_VERSION_PHASE2_V1,
                "included_weight_sum": included_weight_sum,
                "total_template_weight_sum": total_template_weight_sum,
                "coverage_weight_percentage": coverage_weight_percentage,
                "minimum_coverage_weight_percentage": cls.MINIMUM_SCORE_COVERAGE_PERCENTAGE,
                "recommendation": (
                    "Revisar o reemplazar únicamente la evidencia técnicamente insuficiente."
                ),
            }
        )

    @staticmethod
    def _domain_expected(rows: list[tuple], exercise_types: tuple[ExerciseType, ...]) -> bool:
        return any(exercise.type in exercise_types for _, _, exercise, _ in rows)

    @staticmethod
    def _domain_included(rows: list[tuple], exercise_types: tuple[ExerciseType, ...]) -> bool:
        return any(exercise.type in exercise_types for _, _, exercise, _ in rows)

    @classmethod
    def _warning_metadata(cls, rows: list[tuple]) -> dict:
        partial_count = sum(
            bool(score and score.technical_status == TechnicalStatus.PARTIAL)
            for *_, score in rows
        )
        invalid_count = sum(
            bool((score and score.technical_status == TechnicalStatus.INVALID) or score is None)
            for *_, score in rows
        )
        excluded_count = sum(not cls._is_included_score(score) for *_, score in rows)
        manual_review_count = sum(bool(score and score.manual_review_required) for *_, score in rows)

        warning_reasons = []
        if partial_count:
            warning_reasons.append("PARTIAL_EXERCISES")
        if invalid_count:
            warning_reasons.append("INVALID_EXERCISES")
        if excluded_count:
            warning_reasons.append("EXCLUDED_EXERCISES")
        if manual_review_count:
            warning_reasons.append("MANUAL_REVIEW_REQUIRED")

        return {
            "partial_exercise_count": partial_count,
            "invalid_exercise_count": invalid_count,
            "result_status": "COMPLETED_WITH_WARNINGS" if warning_reasons else "COMPLETED",
            "has_warnings": bool(warning_reasons),
            "warning_reasons": warning_reasons,
        }

    @staticmethod
    def _clean_scoring_components(components: dict | None) -> dict:
        cleaned = dict(components or {})
        cleaned.pop("original_scoring_components", None)
        return cleaned

    @staticmethod
    def _original_scoring_components(score: ExerciseScore) -> dict:
        if score.original_scoring_components:
            return FinishAssessmentAttemptUseCase._clean_scoring_components(
                score.original_scoring_components
            )
        nested_original = score.scoring_components.get("original_scoring_components")
        if isinstance(nested_original, dict):
            return FinishAssessmentAttemptUseCase._clean_scoring_components(
                nested_original
            )
        return {}

    @staticmethod
    def _determine_intervention_level(
        final_score: float,
        review_required_count: int,
        writing_review_required_count: int = 0,
    ) -> InterventionLevel:
        if final_score >= 80:
            return InterventionLevel.LOW
        if final_score >= 50:
            return InterventionLevel.MEDIUM
        return InterventionLevel.HIGH
