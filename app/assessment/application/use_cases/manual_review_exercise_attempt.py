from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.exceptions import (
    AssessmentNotFoundError,
    ExerciseAttemptNotFoundError,
    InvalidExerciseTypeError,
    AttemptNotFoundError,
)
from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentRepository,
    AssessmentResultRepository,
    ExerciseAttemptRepository,
    ExerciseRepository,
    ExerciseScoreRepository,
    SpeakingMetricsRepository,
    SpeakingResponseRepository,
    TemplateExerciseRepository,
    WritingMetricsRepository,
    WritingResponseRepository,
)
from app.assessment.domain.enums import ExerciseType, InterventionLevel, TechnicalStatus
from app.assessment.domain.metrics import AssessmentResult, ExerciseScore, SpeakingMetrics, WritingMetrics
from app.assessment.domain.technical_quality import calculate_reading_score
from app.assessment.domain.template import validate_template_exercise_points


SPEAKING_REVIEW_METRICS = {
    "accuracy_score",
    "fluency_score",
    "pronunciation_score",
    "completeness_score",
    "lexical_match",
}
WRITING_REVIEW_METRICS = {"char_accuracy", "word_accuracy"}


@dataclass
class ManualReviewExerciseAttemptCommand:
    exercise_attempt_id: UUID
    teacher_id: UUID
    metrics: dict[str, float]
    teacher_observation: str | None = None


@dataclass
class ManualReviewExerciseAttemptResult:
    exercise_attempt_id: UUID
    exercise_type: ExerciseType
    original_score: float | None
    current_score: float | None
    original_metrics: dict[str, float | None]
    current_metrics: dict[str, float | None]
    score_eligible: bool
    manual_adjustment_applied: bool
    teacher_observation: str | None
    adjusted_by_teacher_id: UUID | None
    adjusted_at: datetime | None
    assessment_result: dict[str, float | None] | None = None


class ManualReviewExerciseAttemptUseCase:
    def __init__(
        self,
        *,
        exercise_attempt_repo: ExerciseAttemptRepository,
        assessment_attempt_repo: AssessmentAttemptRepository,
        assessment_repo: AssessmentRepository,
        template_exercise_repo: TemplateExerciseRepository,
        exercise_repo: ExerciseRepository,
        exercise_score_repo: ExerciseScoreRepository,
        speaking_response_repo: SpeakingResponseRepository,
        speaking_metrics_repo: SpeakingMetricsRepository,
        writing_response_repo: WritingResponseRepository,
        writing_metrics_repo: WritingMetricsRepository,
        result_repo: AssessmentResultRepository,
    ) -> None:
        self._exercise_attempt_repo = exercise_attempt_repo
        self._assessment_attempt_repo = assessment_attempt_repo
        self._assessment_repo = assessment_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._exercise_score_repo = exercise_score_repo
        self._speaking_response_repo = speaking_response_repo
        self._speaking_metrics_repo = speaking_metrics_repo
        self._writing_response_repo = writing_response_repo
        self._writing_metrics_repo = writing_metrics_repo
        self._result_repo = result_repo

    def execute(self, command: ManualReviewExerciseAttemptCommand) -> ManualReviewExerciseAttemptResult:
        self._validate_metric_values(command.metrics)
        exercise_attempt = self._exercise_attempt_repo.find_by_id(command.exercise_attempt_id)
        if not exercise_attempt:
            raise ExerciseAttemptNotFoundError()

        attempt = self._assessment_attempt_repo.find_by_id(exercise_attempt.assessment_attempt_id)
        if not attempt:
            raise AttemptNotFoundError()
        assessment = self._assessment_repo.find_by_id(attempt.assessment_id)
        if not assessment:
            raise AssessmentNotFoundError()
        if assessment.homeroom_teacher_id != command.teacher_id:
            raise AssessmentNotFoundError("Assessment attempt not found.")

        template_exercise = self._template_exercise_repo.find_by_id(exercise_attempt.template_exercise_id)
        exercise = self._exercise_repo.find_by_id(template_exercise.exercise_id)
        if exercise.type == ExerciseType.READING_SPEAKING:
            original_metrics, current_metrics, current_score, current_components = self._review_speaking(
                exercise_attempt.id, command.metrics
            )
        elif exercise.type == ExerciseType.READING_WRITING:
            original_metrics, current_metrics, current_score, current_components = self._review_writing(
                exercise_attempt.id, command.metrics
            )
        else:
            raise InvalidExerciseTypeError(
                "Manual metric review is only allowed for READING_SPEAKING and READING_WRITING exercises."
            )

        existing_score = self._exercise_score_repo.find_by_exercise_attempt_id(exercise_attempt.id)
        if not existing_score:
            raise InvalidExerciseTypeError("Exercise does not have a score to review.")
        if existing_score.technical_status == TechnicalStatus.INVALID:
            raise InvalidExerciseTypeError(
                "Manual review is not allowed for INVALID exercises. New evidence is required."
            )

        now = datetime.now(timezone.utc)
        score_eligible = existing_score.score_eligible or existing_score.technical_status == TechnicalStatus.PARTIAL
        quality_reasons = list(existing_score.quality_reasons)
        if existing_score.technical_status == TechnicalStatus.PARTIAL and "MANUAL_REVIEW_ACCEPTED_PARTIAL" not in quality_reasons:
            quality_reasons.append("MANUAL_REVIEW_ACCEPTED_PARTIAL")
        updated_components = {
            **current_components,
            "manual_adjustment_applied": True,
            "manual_review_overrode_partial": existing_score.technical_status == TechnicalStatus.PARTIAL,
            "original_scoring_components": existing_score.original_scoring_components or existing_score.scoring_components,
        }
        updated_score = self._exercise_score_repo.upsert(
            ExerciseScore(
                id=existing_score.id,
                exercise_attempt_id=existing_score.exercise_attempt_id,
                exercise_type=existing_score.exercise_type,
                score=current_score,
                score_eligible=score_eligible,
                technical_status=existing_score.technical_status,
                manual_review_required=False,
                quality_reasons=quality_reasons,
                scoring_components=updated_components,
                created_at=existing_score.created_at,
                updated_at=now,
                original_score=(
                    existing_score.original_score
                    if existing_score.original_score is not None
                    else existing_score.score
                ),
                current_score=current_score,
                original_scoring_components=(
                    existing_score.original_scoring_components
                    if existing_score.original_scoring_components
                    else existing_score.scoring_components
                ),
                current_scoring_components=updated_components,
                manual_adjustment_applied=True,
                teacher_observation=command.teacher_observation,
                adjusted_by_teacher_id=command.teacher_id,
                adjusted_at=now,
            )
        )

        assessment_result = self._recalculate_result_if_exists(attempt.id)
        return ManualReviewExerciseAttemptResult(
            exercise_attempt_id=exercise_attempt.id,
            exercise_type=exercise.type,
            original_score=updated_score.original_score,
            current_score=updated_score.current_score,
            original_metrics=original_metrics,
            current_metrics=current_metrics,
            score_eligible=updated_score.score_eligible,
            manual_adjustment_applied=updated_score.manual_adjustment_applied,
            teacher_observation=updated_score.teacher_observation,
            adjusted_by_teacher_id=updated_score.adjusted_by_teacher_id,
            adjusted_at=updated_score.adjusted_at,
            assessment_result=assessment_result,
        )

    def _review_speaking(
        self, exercise_attempt_id: UUID, updates: dict[str, float]
    ) -> tuple[dict[str, float | None], dict[str, float | None], float, dict]:
        self._validate_metric_names(updates, SPEAKING_REVIEW_METRICS)
        response = self._speaking_response_repo.find_by_exercise_attempt_id(exercise_attempt_id)
        if not response:
            raise InvalidExerciseTypeError("Speaking response not found for manual review.")
        metrics = self._speaking_metrics_repo.find_by_speaking_response_id(response.id)
        if not metrics:
            raise InvalidExerciseTypeError("Speaking metrics not found for manual review.")

        original = {
            "accuracy_score": metrics.original_accuracy_score if metrics.original_accuracy_score is not None else metrics.accuracy_score,
            "fluency_score": metrics.original_fluency_score if metrics.original_fluency_score is not None else metrics.fluency_score,
            "pronunciation_score": metrics.original_pronunciation_score if metrics.original_pronunciation_score is not None else metrics.pronunciation_score,
            "completeness_score": metrics.original_completeness_score if metrics.original_completeness_score is not None else metrics.completeness_score,
            "lexical_match": metrics.original_lexical_match if metrics.original_lexical_match is not None else (metrics.comparison_json or {}).get("lexical_match_percentage"),
        }
        current = {
            "accuracy_score": metrics.current_accuracy_score if metrics.current_accuracy_score is not None else metrics.accuracy_score,
            "fluency_score": metrics.current_fluency_score if metrics.current_fluency_score is not None else metrics.fluency_score,
            "pronunciation_score": metrics.current_pronunciation_score if metrics.current_pronunciation_score is not None else metrics.pronunciation_score,
            "completeness_score": metrics.current_completeness_score if metrics.current_completeness_score is not None else metrics.completeness_score,
            "lexical_match": metrics.current_lexical_match if metrics.current_lexical_match is not None else (metrics.comparison_json or {}).get("lexical_match_percentage"),
        }
        current.update(updates)
        score, components = calculate_reading_score(
            pronunciation_score=current["pronunciation_score"],
            accuracy_score=current["accuracy_score"],
            fluency_score=current["fluency_score"],
            completeness_score=current["completeness_score"],
            lexical_match=current["lexical_match"],
        )
        if score is None:
            raise InvalidExerciseTypeError("At least one speaking metric is required to calculate current_score.")

        metrics.pronunciation_score = current["pronunciation_score"]
        metrics.accuracy_score = current["accuracy_score"]
        metrics.fluency_score = current["fluency_score"]
        metrics.completeness_score = current["completeness_score"]
        metrics.original_pronunciation_score = original["pronunciation_score"]
        metrics.current_pronunciation_score = current["pronunciation_score"]
        metrics.original_accuracy_score = original["accuracy_score"]
        metrics.current_accuracy_score = current["accuracy_score"]
        metrics.original_fluency_score = original["fluency_score"]
        metrics.current_fluency_score = current["fluency_score"]
        metrics.original_completeness_score = original["completeness_score"]
        metrics.current_completeness_score = current["completeness_score"]
        metrics.original_lexical_match = original["lexical_match"]
        metrics.current_lexical_match = current["lexical_match"]
        self._speaking_metrics_repo.update(metrics)
        return original, current, score, components

    def _review_writing(
        self, exercise_attempt_id: UUID, updates: dict[str, float]
    ) -> tuple[dict[str, float | None], dict[str, float | None], float, dict]:
        self._validate_metric_names(updates, WRITING_REVIEW_METRICS)
        response = self._writing_response_repo.find_by_exercise_attempt_id(exercise_attempt_id)
        if not response:
            raise InvalidExerciseTypeError("Writing response not found for manual review.")
        metrics = self._writing_metrics_repo.find_by_writing_response_id(response.id)
        if not metrics:
            raise InvalidExerciseTypeError("Writing metrics not found for manual review.")

        char_from_cer = round(max(0.0, 100.0 * (1.0 - metrics.cer)), 2) if metrics.cer is not None else None
        word_from_wer = round(max(0.0, 100.0 * (1.0 - metrics.wer)), 2) if metrics.wer is not None else None
        original = {
            "char_accuracy": metrics.original_char_accuracy if metrics.original_char_accuracy is not None else char_from_cer,
            "word_accuracy": metrics.original_word_accuracy if metrics.original_word_accuracy is not None else word_from_wer,
        }
        current = {
            "char_accuracy": metrics.current_char_accuracy if metrics.current_char_accuracy is not None else original["char_accuracy"],
            "word_accuracy": metrics.current_word_accuracy if metrics.current_word_accuracy is not None else original["word_accuracy"],
        }
        current.update(updates)
        if current["char_accuracy"] is None or current["word_accuracy"] is None:
            raise InvalidExerciseTypeError("char_accuracy and word_accuracy are required to calculate current_score.")
        current_similarity = round(0.75 * current["char_accuracy"] + 0.25 * current["word_accuracy"], 2)
        original_similarity = (
            metrics.original_similarity_score
            if metrics.original_similarity_score is not None
            else metrics.similarity_score
        )

        metrics.similarity_score = current_similarity
        metrics.original_char_accuracy = original["char_accuracy"]
        metrics.current_char_accuracy = current["char_accuracy"]
        metrics.original_word_accuracy = original["word_accuracy"]
        metrics.current_word_accuracy = current["word_accuracy"]
        metrics.original_similarity_score = original_similarity
        metrics.current_similarity_score = current_similarity
        self._writing_metrics_repo.update(metrics)
        components = {
            "formula_version": "phase2_v1",
            "formula": "0.75_char_accuracy + 0.25_word_accuracy",
            "component_weights": {"char_accuracy": 0.75, "word_accuracy": 0.25},
            "char_accuracy": current["char_accuracy"],
            "word_accuracy": current["word_accuracy"],
            "similarity_score": current_similarity,
        }
        return original, {**current, "similarity_score": current_similarity}, current_similarity, components

    def _recalculate_result_if_exists(self, attempt_id: UUID) -> dict[str, float | None] | None:
        result = self._result_repo.find_by_attempt_id(attempt_id)
        if not result:
            return None

        rows = []
        exercise_attempts = self._exercise_attempt_repo.find_by_assessment_attempt_id(attempt_id)
        canonical = {
            score.exercise_attempt_id: score
            for score in self._exercise_score_repo.find_by_assessment_attempt_id(attempt_id)
        }
        for exercise_attempt in exercise_attempts:
            template_exercise = self._template_exercise_repo.find_by_id(exercise_attempt.template_exercise_id)
            validate_template_exercise_points(template_exercise.points)
            exercise = self._exercise_repo.find_by_id(template_exercise.exercise_id)
            rows.append((exercise_attempt, template_exercise, exercise, canonical.get(exercise_attempt.id)))

        included_rows = [
            row for row in rows if row[3] and row[3].score_eligible and self._current_score(row[3]) is not None
        ]
        if not included_rows:
            return {
                "original_final_score": result.original_final_score if result.original_final_score is not None else result.final_score,
                "current_final_score": None,
            }

        included = [score for *_, score in included_rows]
        included_weight_sum = sum(template_exercise.points for _, template_exercise, _, _ in included_rows)
        total_template_weight_sum = sum(template_exercise.points for _, template_exercise, _, _ in rows)
        current_final_score = sum(
            self._current_score(score) * template_exercise.points
            for _, template_exercise, _, score in included_rows
        ) / included_weight_sum
        current_final_score = round(max(0.0, min(100.0, current_final_score)), 2)
        review_required_count = sum(score.manual_review_required for score in included)
        writing_review_count = sum(
            score.manual_review_required
            for score in included
            if score.exercise_type == ExerciseType.READING_WRITING
        )
        speaking_scores = [
            self._current_score(score)
            for score in included
            if score.exercise_type == ExerciseType.READING_SPEAKING and self._current_score(score) is not None
        ]
        writing_scores = [
            self._current_score(score)
            for score in included
            if score.exercise_type == ExerciseType.READING_WRITING and self._current_score(score) is not None
        ]
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
                included_exercise_count=len(included_rows),
                total_exercise_count=len(rows),
                coverage_weight_percentage=coverage_weight_percentage,
            )
            for row in rows
        ]
        original_final_score = result.original_final_score if result.original_final_score is not None else result.final_score
        original_snapshot = (
            result.original_scoring_snapshot_json
            if result.original_scoring_snapshot_json is not None
            else result.scoring_snapshot_json
        )
        self._result_repo.update(
            AssessmentResult(
                id=result.id,
                assessment_attempt_id=result.assessment_attempt_id,
                final_score=current_final_score,
                max_score=result.max_score,
                mc_correct_count=result.mc_correct_count,
                os_correct_count=result.os_correct_count,
                speaking_completed_count=sum(score.exercise_type == ExerciseType.READING_SPEAKING for score in included),
                writing_completed_count=sum(score.exercise_type == ExerciseType.READING_WRITING for score in included),
                intervention_level=self._determine_intervention_level(
                    current_final_score, review_required_count, writing_review_count
                ),
                generated_at=result.generated_at,
                created_at=result.created_at,
                updated_at=datetime.now(timezone.utc),
                speaking_average_score=(sum(speaking_scores) / len(speaking_scores) if speaking_scores else None),
                speaking_review_required_count=sum(
                    score.manual_review_required
                    for score in included
                    if score.exercise_type == ExerciseType.READING_SPEAKING
                ),
                total_exercises=len(rows),
                evaluated_exercises=len(included),
                pending_exercises=len(rows) - len(included),
                writing_average_score=(sum(writing_scores) / len(writing_scores) if writing_scores else None),
                writing_review_required_count=writing_review_count,
                score_denominator=included_weight_sum,
                scoring_snapshot_json=snapshot,
                original_final_score=original_final_score,
                current_final_score=current_final_score,
                original_scoring_snapshot_json=original_snapshot,
                current_scoring_snapshot_json=snapshot,
            )
        )
        return {
            "original_final_score": original_final_score,
            "current_final_score": current_final_score,
        }

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
        current_score = ManualReviewExerciseAttemptUseCase._current_score(score)
        included = bool(score and score.score_eligible and current_score is not None)
        return {
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
            "technical_status": score.technical_status.value if score else "INVALID",
            "manual_review_required": score.manual_review_required if score else True,
            "quality_reasons": score.quality_reasons if score else ["MISSING_CANONICAL_SCORE"],
            "scoring_components": score.current_scoring_components or score.scoring_components if score else {},
            "original_scoring_components": score.original_scoring_components if score else {},
            "current_scoring_components": score.current_scoring_components or score.scoring_components if score else {},
            "manual_adjustment_applied": score.manual_adjustment_applied if score else False,
            "teacher_observation": score.teacher_observation if score else None,
            "adjusted_by_teacher_id": str(score.adjusted_by_teacher_id) if score and score.adjusted_by_teacher_id else None,
            "adjusted_at": score.adjusted_at.isoformat() if score and score.adjusted_at else None,
            "weighted_contribution": current_score * template_exercise.points if included and score else None,
            "effective_weight": template_exercise.points if included else None,
            "effective_weight_percentage": (
                round((template_exercise.points / included_weight_sum) * 100, 2)
                if included and included_weight_sum
                else None
            ),
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

    @staticmethod
    def _validate_metric_values(metrics: dict[str, float]) -> None:
        if not metrics:
            raise InvalidExerciseTypeError("At least one metric is required for manual review.")
        for name, value in metrics.items():
            if not isinstance(value, int | float) or value < 0 or value > 100:
                raise InvalidExerciseTypeError(f"Metric '{name}' must be a number between 0 and 100.")

    @staticmethod
    def _validate_metric_names(metrics: dict[str, float], allowed: set[str]) -> None:
        invalid = sorted(set(metrics) - allowed)
        if invalid:
            raise InvalidExerciseTypeError(f"Metrics are not editable for this exercise type: {', '.join(invalid)}.")
