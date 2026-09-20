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
    ExpectedAnswerRepository,
    PromptExerciseRepository,
    SpeakingMetricsRepository,
    SpeakingResponseRepository,
    TemplateExerciseRepository,
    WritingMetricsRepository,
    WritingResponseRepository,
)
from app.assessment.domain.enums import ExerciseType, InterventionLevel, TechnicalStatus
from app.assessment.domain.metrics import AssessmentResult, ExerciseScore, SpeakingMetrics, WritingMetrics
from app.assessment.domain.text_comparison import compare_texts
from app.assessment.domain.technical_quality import calculate_reading_score
from app.assessment.domain.template import validate_template_exercise_points
from app.assessment.domain.writing_text_comparison import determine_writing_review


SPEAKING_REVIEW_METRICS = {
    "accuracy_score",
    "fluency_score",
    "pronunciation_score",
    "completeness_score",
    "lexical_match",
}
WRITING_REVIEW_METRICS = {"char_accuracy", "word_accuracy"}
MANUAL_REVIEW_ACTION_CONFIRM = "confirm"
MANUAL_REVIEW_ACTION_OVERRIDE_METRICS = "override_metrics"
MANUAL_REVIEW_ACTION_CORRECT_EVIDENCE = "correct_evidence"
MANUAL_REVIEW_ACTIONS = {
    MANUAL_REVIEW_ACTION_CONFIRM,
    MANUAL_REVIEW_ACTION_OVERRIDE_METRICS,
    MANUAL_REVIEW_ACTION_CORRECT_EVIDENCE,
}


@dataclass
class ManualReviewExerciseAttemptCommand:
    exercise_attempt_id: UUID
    teacher_id: UUID
    metrics: dict[str, float] | None = None
    corrections: dict | None = None
    action: str = MANUAL_REVIEW_ACTION_OVERRIDE_METRICS
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
    review_status: str
    metric_sources: dict | None
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
        prompt_exercise_repo: PromptExerciseRepository,
        expected_answer_repo: ExpectedAnswerRepository,
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
        self._prompt_exercise_repo = prompt_exercise_repo
        self._expected_answer_repo = expected_answer_repo
        self._exercise_score_repo = exercise_score_repo
        self._speaking_response_repo = speaking_response_repo
        self._speaking_metrics_repo = speaking_metrics_repo
        self._writing_response_repo = writing_response_repo
        self._writing_metrics_repo = writing_metrics_repo
        self._result_repo = result_repo

    def execute(self, command: ManualReviewExerciseAttemptCommand) -> ManualReviewExerciseAttemptResult:
        action = command.action or MANUAL_REVIEW_ACTION_OVERRIDE_METRICS
        self._validate_action(action)
        teacher_observation = self._validate_teacher_observation(command.teacher_observation)
        if action == MANUAL_REVIEW_ACTION_OVERRIDE_METRICS:
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
        existing_score = self._exercise_score_repo.find_by_exercise_attempt_id(exercise_attempt.id)
        if not existing_score:
            raise InvalidExerciseTypeError("Exercise does not have a score to review.")
        if existing_score.technical_status == TechnicalStatus.INVALID:
            raise InvalidExerciseTypeError(
                "Manual review is not allowed for INVALID exercises. New evidence is required."
            )

        if action == MANUAL_REVIEW_ACTION_CONFIRM:
            original_metrics, current_metrics, current_score, current_components = self._confirm_review(
                exercise.type, exercise_attempt.id, existing_score
            )
            manual_adjustment_applied = False
            review_status = "confirmed"
        elif action == MANUAL_REVIEW_ACTION_OVERRIDE_METRICS and exercise.type == ExerciseType.READING_SPEAKING:
            original_metrics, current_metrics, current_score, current_components = self._review_speaking(
                exercise_attempt.id, command.metrics or {}
            )
            manual_adjustment_applied = True
            review_status = "overridden"
        elif action == MANUAL_REVIEW_ACTION_OVERRIDE_METRICS and exercise.type == ExerciseType.READING_WRITING:
            original_metrics, current_metrics, current_score, current_components = self._review_writing(
                exercise_attempt.id, command.metrics or {}
            )
            manual_adjustment_applied = True
            review_status = "overridden"
        elif action == MANUAL_REVIEW_ACTION_CORRECT_EVIDENCE and exercise.type == ExerciseType.READING_SPEAKING:
            original_metrics, current_metrics, current_score, current_components, metric_sources = self._correct_speaking_evidence(
                exercise.id, exercise_attempt.id, command.corrections
            )
            manual_adjustment_applied = True
            review_status = "overridden"
        elif action == MANUAL_REVIEW_ACTION_CORRECT_EVIDENCE and exercise.type == ExerciseType.READING_WRITING:
            original_metrics, current_metrics, current_score, current_components, metric_sources = self._correct_writing_evidence(
                exercise.id, exercise_attempt.id, command.corrections
            )
            manual_adjustment_applied = True
            review_status = "overridden"
        else:
            raise InvalidExerciseTypeError(
                "Manual metric review is only allowed for READING_SPEAKING and READING_WRITING exercises."
            )
        if action != MANUAL_REVIEW_ACTION_CORRECT_EVIDENCE:
            metric_sources = self._metric_sources_for_action(action, exercise.type, command.metrics or {})

        now = datetime.now(timezone.utc)
        score_eligible = existing_score.score_eligible or existing_score.technical_status == TechnicalStatus.PARTIAL
        quality_reasons = list(existing_score.quality_reasons)
        if existing_score.technical_status == TechnicalStatus.PARTIAL and "MANUAL_REVIEW_ACCEPTED_PARTIAL" not in quality_reasons:
            quality_reasons.append("MANUAL_REVIEW_ACCEPTED_PARTIAL")
        original_components = self._original_scoring_components(existing_score)
        updated_components = {
            **self._clean_scoring_components(current_components),
            "manual_adjustment_applied": manual_adjustment_applied,
            "review_status": review_status,
            "manual_review_overrode_partial": existing_score.technical_status == TechnicalStatus.PARTIAL,
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
                original_scoring_components=original_components,
                current_scoring_components=updated_components,
                manual_adjustment_applied=manual_adjustment_applied,
                review_status=review_status,
                metric_sources=metric_sources,
                teacher_observation=teacher_observation,
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
            review_status=self._review_status(updated_score),
            metric_sources=updated_score.metric_sources,
            teacher_observation=updated_score.teacher_observation,
            adjusted_by_teacher_id=updated_score.adjusted_by_teacher_id,
            adjusted_at=updated_score.adjusted_at,
            assessment_result=assessment_result,
        )

    def _confirm_review(
        self,
        exercise_type: ExerciseType,
        exercise_attempt_id: UUID,
        existing_score: ExerciseScore,
    ) -> tuple[dict[str, float | None], dict[str, float | None], float, dict]:
        if exercise_type == ExerciseType.READING_SPEAKING:
            original, current = self._speaking_metric_snapshots(exercise_attempt_id)
        elif exercise_type == ExerciseType.READING_WRITING:
            original, current = self._writing_metric_snapshots(exercise_attempt_id)
        else:
            raise InvalidExerciseTypeError(
                "Manual metric review is only allowed for READING_SPEAKING and READING_WRITING exercises."
            )
        current_score = self._current_score(existing_score)
        if current_score is None:
            raise InvalidExerciseTypeError("Exercise does not have a current score to confirm.")
        components = self._clean_scoring_components(
            existing_score.current_scoring_components or existing_score.scoring_components
        )
        return original, current, current_score, components

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

    def _correct_speaking_evidence(
        self,
        exercise_id: UUID,
        exercise_attempt_id: UUID,
        corrections: dict | None,
    ) -> tuple[dict[str, float | None], dict[str, float | None], float, dict, dict]:
        reviewed_text = self._string_correction(
            corrections, "free_transcription_text", allow_empty=False
        )
        expected_text = self._expected_text_for_exercise(exercise_id)
        response = self._speaking_response_repo.find_by_exercise_attempt_id(exercise_attempt_id)
        if not response:
            raise InvalidExerciseTypeError("Speaking response not found for manual review.")
        metrics = self._speaking_metrics_repo.find_by_speaking_response_id(response.id)
        if not metrics:
            raise InvalidExerciseTypeError("Speaking metrics not found for manual review.")

        comparison = compare_texts(expected_text, reviewed_text).to_dict()
        lexical_match = comparison.get("lexical_match_percentage")
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
            "lexical_match": lexical_match,
        }
        score, components = calculate_reading_score(
            pronunciation_score=current["pronunciation_score"],
            accuracy_score=current["accuracy_score"],
            fluency_score=current["fluency_score"],
            completeness_score=current["completeness_score"],
            lexical_match=current["lexical_match"],
        )
        if score is None:
            raise InvalidExerciseTypeError("At least one speaking metric is required to calculate current_score.")

        response.reviewed_free_transcription_text = reviewed_text
        self._speaking_response_repo.update(response)
        metrics.original_accuracy_score = original["accuracy_score"]
        metrics.original_fluency_score = original["fluency_score"]
        metrics.original_pronunciation_score = original["pronunciation_score"]
        metrics.original_completeness_score = original["completeness_score"]
        metrics.original_lexical_match = original["lexical_match"]
        metrics.current_accuracy_score = current["accuracy_score"]
        metrics.current_fluency_score = current["fluency_score"]
        metrics.current_pronunciation_score = current["pronunciation_score"]
        metrics.current_completeness_score = current["completeness_score"]
        metrics.current_lexical_match = lexical_match
        self._speaking_metrics_repo.update(metrics)

        components = {
            **components,
            "reviewed_analysis": comparison,
            "reviewed_free_transcription_text": reviewed_text,
        }
        metric_sources = {
            "accuracy_score": "automatic",
            "fluency_score": "automatic",
            "pronunciation_score": "automatic",
            "completeness_score": "automatic",
            "lexical_match": "recalculated_from_reviewed_evidence",
        }
        return original, current, score, components, metric_sources

    def _speaking_metric_snapshots(
        self, exercise_attempt_id: UUID
    ) -> tuple[dict[str, float | None], dict[str, float | None]]:
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
        return original, current

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

    def _correct_writing_evidence(
        self,
        exercise_id: UUID,
        exercise_attempt_id: UUID,
        corrections: dict | None,
    ) -> tuple[dict[str, float | None], dict[str, float | None], float, dict, dict]:
        reviewed_text = self._string_correction(corrections, "recognized_text", allow_empty=False)
        expected_text = self._expected_text_for_exercise(exercise_id)
        response = self._writing_response_repo.find_by_exercise_attempt_id(exercise_attempt_id)
        if not response:
            raise InvalidExerciseTypeError("Writing response not found for manual review.")
        metrics = self._writing_metrics_repo.find_by_writing_response_id(response.id)
        if not metrics:
            raise InvalidExerciseTypeError("Writing metrics not found for manual review.")

        review = determine_writing_review(expected_text, reviewed_text, confidence_avg=metrics.confidence_avg)
        original = {
            "char_accuracy": metrics.original_char_accuracy if metrics.original_char_accuracy is not None else self._char_accuracy_from_cer(metrics.cer),
            "word_accuracy": metrics.original_word_accuracy if metrics.original_word_accuracy is not None else self._word_accuracy_from_wer(metrics.wer),
            "similarity_score": metrics.original_similarity_score if metrics.original_similarity_score is not None else metrics.similarity_score,
        }
        current = {
            "char_accuracy": review.char_accuracy,
            "word_accuracy": review.word_accuracy,
            "similarity_score": review.similarity_score,
        }

        response.reviewed_recognized_text = reviewed_text
        self._writing_response_repo.update(response)
        metrics.original_char_accuracy = original["char_accuracy"]
        metrics.original_word_accuracy = original["word_accuracy"]
        metrics.original_similarity_score = original["similarity_score"]
        metrics.current_char_accuracy = current["char_accuracy"]
        metrics.current_word_accuracy = current["word_accuracy"]
        metrics.current_similarity_score = current["similarity_score"]
        metrics.similarity_score = current["similarity_score"]
        self._writing_metrics_repo.update(metrics)

        reviewed_analysis = {
            "recognized_text": reviewed_text,
            "cer": review.cer,
            "wer": review.wer,
            "char_accuracy": review.char_accuracy,
            "word_accuracy": review.word_accuracy,
            "similarity_score": review.similarity_score,
            "review_required": review.review_required,
            "review_reasons": review.review_reasons,
        }
        components = {
            "formula_version": "phase2_v1",
            "formula": "0.75_char_accuracy + 0.25_word_accuracy",
            "component_weights": {"char_accuracy": 0.75, "word_accuracy": 0.25},
            "char_accuracy": current["char_accuracy"],
            "word_accuracy": current["word_accuracy"],
            "similarity_score": current["similarity_score"],
            "reviewed_analysis": reviewed_analysis,
            "reviewed_recognized_text": reviewed_text,
        }
        metric_sources = {
            "char_accuracy": "recalculated_from_reviewed_evidence",
            "word_accuracy": "recalculated_from_reviewed_evidence",
            "similarity_score": "recalculated_from_reviewed_evidence",
        }
        return original, current, current["similarity_score"], components, metric_sources

    def _writing_metric_snapshots(
        self, exercise_attempt_id: UUID
    ) -> tuple[dict[str, float | None], dict[str, float | None]]:
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
            "similarity_score": metrics.original_similarity_score if metrics.original_similarity_score is not None else metrics.similarity_score,
        }
        current = {
            "char_accuracy": metrics.current_char_accuracy if metrics.current_char_accuracy is not None else original["char_accuracy"],
            "word_accuracy": metrics.current_word_accuracy if metrics.current_word_accuracy is not None else original["word_accuracy"],
            "similarity_score": metrics.current_similarity_score if metrics.current_similarity_score is not None else metrics.similarity_score,
        }
        return original, current

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
            row for row in rows if self._is_included_score(row[3])
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
        warning_metadata = self._warning_metadata(rows)
        snapshot = [
            self._snapshot_row(
                *row,
                included_weight_sum=included_weight_sum,
                total_template_weight_sum=total_template_weight_sum,
                included_exercise_count=len(included_rows),
                total_exercise_count=len(rows),
                coverage_weight_percentage=coverage_weight_percentage,
                partial_exercise_count=warning_metadata["partial_exercise_count"],
                invalid_exercise_count=warning_metadata["invalid_exercise_count"],
                result_status=warning_metadata["result_status"],
                has_warnings=warning_metadata["has_warnings"],
                warning_reasons=warning_metadata["warning_reasons"],
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
        partial_exercise_count: int,
        invalid_exercise_count: int,
        result_status: str,
        has_warnings: bool,
        warning_reasons: list[str],
    ) -> dict:
        current_score = ManualReviewExerciseAttemptUseCase._current_score(score)
        included = ManualReviewExerciseAttemptUseCase._is_included_score(score)
        current_components = ManualReviewExerciseAttemptUseCase._clean_scoring_components(
            score.current_scoring_components or score.scoring_components if score else {}
        )
        original_components = (
            ManualReviewExerciseAttemptUseCase._original_scoring_components(score)
            if score
            else {}
        )
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
            "review_status": ManualReviewExerciseAttemptUseCase._review_status(score),
            "metric_sources": score.metric_sources if score else None,
            "quality_reasons": score.quality_reasons if score else ["MISSING_CANONICAL_SCORE"],
            "scoring_components": current_components,
            "original_scoring_components": original_components,
            "current_scoring_components": current_components,
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
        if score is None or ManualReviewExerciseAttemptUseCase._current_score(score) is None:
            return False
        return score.score_eligible or score.technical_status == TechnicalStatus.PARTIAL

    @staticmethod
    def _review_status(score: ExerciseScore | None) -> str:
        if score is None:
            return "pending"
        if score.review_status:
            return score.review_status
        if score.manual_adjustment_applied:
            return "overridden"
        if score.manual_review_required:
            return "pending"
        return "not_required"

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
            return ManualReviewExerciseAttemptUseCase._clean_scoring_components(
                score.original_scoring_components
            )
        nested_original = score.scoring_components.get("original_scoring_components")
        if isinstance(nested_original, dict):
            return ManualReviewExerciseAttemptUseCase._clean_scoring_components(
                nested_original
            )
        return ManualReviewExerciseAttemptUseCase._clean_scoring_components(
            score.scoring_components
        )

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

    @staticmethod
    def _validate_action(action: str) -> None:
        if action not in MANUAL_REVIEW_ACTIONS:
            raise InvalidExerciseTypeError(f"Unsupported manual review action: {action}.")

    @staticmethod
    def _validate_teacher_observation(teacher_observation: str | None) -> str:
        if not teacher_observation or not teacher_observation.strip():
            raise InvalidExerciseTypeError("teacher_observation is required for manual review.")
        return teacher_observation.strip()

    @staticmethod
    def _metric_sources_for_action(action: str, exercise_type: ExerciseType, metrics: dict[str, float]) -> dict | None:
        if action == MANUAL_REVIEW_ACTION_CONFIRM:
            return None
        if action != MANUAL_REVIEW_ACTION_OVERRIDE_METRICS:
            return None
        if exercise_type == ExerciseType.READING_SPEAKING:
            names = SPEAKING_REVIEW_METRICS
        elif exercise_type == ExerciseType.READING_WRITING:
            names = WRITING_REVIEW_METRICS | {"similarity_score"}
        else:
            return None
        return {
            name: "teacher_override" if name in metrics else "automatic"
            for name in sorted(names)
        }

    def _expected_text_for_exercise(self, exercise_id: UUID) -> str:
        prompt = self._prompt_exercise_repo.find_by_exercise_id(exercise_id)
        expected = self._expected_answer_repo.find_by_prompt_exercise_id(prompt.id) if prompt else None
        expected_text = expected.expected_text if expected else (prompt.text_to_show if prompt else None)
        if not expected_text:
            raise InvalidExerciseTypeError("Expected text not found for manual review.")
        return expected_text

    @staticmethod
    def _string_correction(corrections: dict | None, key: str, *, allow_empty: bool) -> str:
        if not isinstance(corrections, dict) or key not in corrections:
            raise InvalidExerciseTypeError(f"corrections.{key} is required for correct_evidence.")
        value = corrections[key]
        if not isinstance(value, str):
            raise InvalidExerciseTypeError(f"corrections.{key} must be a string.")
        value = value.strip()
        if not allow_empty and not value:
            raise InvalidExerciseTypeError(f"corrections.{key} must not be empty.")
        return value

    @staticmethod
    def _char_accuracy_from_cer(cer: float | None) -> float | None:
        return round(max(0.0, 100.0 * (1.0 - cer)), 2) if cer is not None else None

    @staticmethod
    def _word_accuracy_from_wer(wer: float | None) -> float | None:
        return round(max(0.0, 100.0 * (1.0 - wer)), 2) if wer is not None else None
