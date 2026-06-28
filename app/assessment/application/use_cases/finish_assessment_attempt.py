from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.exceptions import (
    AttemptAlreadyCompletedError,
    AttemptNotFoundError,
    ExerciseAttemptNotFoundError,
)
from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentResultRepository,
    ExerciseAttemptRepository,
    ExerciseRepository,
    ExpectedAnswerRepository,
    MCResponseRepository,
    OSResponseRepository,
    PromptExerciseRepository,
    SpeakingMetricsRepository,
    SpeakingResponseRepository,
    TemplateExerciseRepository,
    WritingMetricsRepository,
    WritingResponseRepository,
)
from app.assessment.domain.enums import AttemptStatus, ExerciseAttemptStatus, ExerciseType, InterventionLevel
from app.assessment.domain.metrics import AssessmentResult
from app.assessment.domain.response import SpeakingResponse
from app.assessment.domain.text_comparison import compare_texts


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
        speaking_metrics_repo: SpeakingMetricsRepository,
        writing_metrics_repo: WritingMetricsRepository,
        prompt_exercise_repo: PromptExerciseRepository,
        expected_answer_repo: ExpectedAnswerRepository,
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
        self._speaking_metrics_repo = speaking_metrics_repo
        self._writing_metrics_repo = writing_metrics_repo
        self._prompt_exercise_repo = prompt_exercise_repo
        self._expected_answer_repo = expected_answer_repo
        self._result_repo = result_repo

    def execute(self, command: FinishAssessmentAttemptCommand) -> AssessmentResult:
        attempt = self._attempt_repo.find_by_id(command.attempt_id)
        if not attempt:
            raise AttemptNotFoundError()
        if attempt.status == AttemptStatus.COMPLETED:
            raise AttemptAlreadyCompletedError()

        exercise_attempts = self._exercise_attempt_repo.find_by_assessment_attempt_id(attempt.id)

        total_score = 0.0
        total_exercises = 0
        scored_exercises = 0
        evaluated_exercises = 0
        mc_correct = 0
        os_correct = 0
        speaking_done = 0
        writing_done = 0
        review_required_count = 0
        any_failed = False
        speaking_scores: list[float] = []
        writing_scores: list[float] = []
        writing_review_count = 0

        for ea in exercise_attempts:
            te = self._template_exercise_repo.find_by_id(ea.template_exercise_id)
            exercise = self._exercise_repo.find_by_id(te.exercise_id)

            if te.is_required and ea.status == ExerciseAttemptStatus.PENDING:
                raise ExerciseAttemptNotFoundError(
                    f"Exercise attempt {ea.id} is still PENDING. Complete all required exercises before finishing."
                )

            etype = exercise.type

            if etype == ExerciseType.MULTIPLE_CHOICE:
                total_exercises += 1
                resp = self._mc_response_repo.find_by_exercise_attempt_id(ea.id)
                if resp and resp.is_correct:
                    total_score += 100.0
                    mc_correct += 1
                if resp:
                    evaluated_exercises += 1
                    scored_exercises += 1

            elif etype == ExerciseType.ORDER_SYLLABLES:
                total_exercises += 1
                resp = self._os_response_repo.find_by_exercise_attempt_id(ea.id)
                if resp and resp.is_correct:
                    total_score += 100.0
                    os_correct += 1
                if resp:
                    evaluated_exercises += 1
                    scored_exercises += 1

            elif etype in (ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING):
                total_exercises += 1
                speaking_resp = self._speaking_response_repo.find_by_exercise_attempt_id(ea.id)
                if speaking_resp:
                    speaking_done += 1
                    evaluated_exercises += 1
                    scored_exercises += 1
                    speaking_score, needs_review, is_failed = self._evaluate_speaking(
                        exercise.id, speaking_resp
                    )
                    if speaking_score is not None:
                        total_score += speaking_score
                        speaking_scores.append(speaking_score)
                    if needs_review:
                        review_required_count += 1
                    if is_failed:
                        any_failed = True

            elif etype in (ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING):
                total_exercises += 1
                resp = self._writing_response_repo.find_by_exercise_attempt_id(ea.id)
                if resp:
                    writing_done += 1
                    evaluated_exercises += 1
                    metrics = self._writing_metrics_repo.find_by_writing_response_id(resp.id)
                    if metrics and metrics.similarity_score is not None:
                        scored_exercises += 1
                        total_score += metrics.similarity_score
                        writing_scores.append(metrics.similarity_score)
                        if metrics.similarity_score < 75:
                            writing_review_count += 1

        final_score = (total_score / scored_exercises) if scored_exercises > 0 else None
        speaking_average_score = sum(speaking_scores) / len(speaking_scores) if speaking_scores else None
        writing_average_score = sum(writing_scores) / len(writing_scores) if writing_scores else None
        combined_review_count = review_required_count + writing_review_count

        if scored_exercises == 0:
            level = None
        else:
            level = self._determine_intervention_level(
                final_score or 0.0, combined_review_count, any_failed, writing_review_count
            )

        now = datetime.now(timezone.utc)
        attempt.status = AttemptStatus.COMPLETED
        attempt.completed_at = now
        self._attempt_repo.update(attempt)

        result = self._result_repo.create(
            AssessmentResult(
                id=UUID(int=0),
                assessment_attempt_id=attempt.id,
                final_score=round(final_score, 2) if final_score is not None else None,
                max_score=float(scored_exercises * 100) if scored_exercises > 0 else None,
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
        result.speaking_average_score = speaking_average_score
        result.speaking_review_required_count = review_required_count
        result.total_exercises = total_exercises
        result.evaluated_exercises = evaluated_exercises
        result.pending_exercises = total_exercises - evaluated_exercises
        result.writing_average_score = writing_average_score
        result.writing_review_required_count = writing_review_count
        return result

    def _evaluate_speaking(
        self, exercise_id: UUID, speaking_resp: SpeakingResponse
    ) -> tuple[float | None, bool, bool]:
        metrics = self._speaking_metrics_repo.find_by_speaking_response_id(speaking_resp.id)
        if metrics is None:
            return (None, True, True)

        all_scores_none = all(
            x is None
            for x in (
                metrics.pronunciation_score,
                metrics.accuracy_score,
                metrics.completeness_score,
            )
        )
        is_failed = all_scores_none and not speaking_resp.free_transcription_text

        components: list[float] = []
        if metrics.pronunciation_score is not None:
            components.append(metrics.pronunciation_score)
        if metrics.accuracy_score is not None:
            components.append(metrics.accuracy_score)
        if metrics.completeness_score is not None:
            components.append(metrics.completeness_score)

        lexical_match: float | None = None
        prompt_exercise = self._prompt_exercise_repo.find_by_exercise_id(exercise_id)
        if prompt_exercise:
            expected_answer = self._expected_answer_repo.find_by_prompt_exercise_id(prompt_exercise.id)
            if expected_answer and speaking_resp.free_transcription_text:
                comparison = compare_texts(expected_answer.expected_text, speaking_resp.free_transcription_text)
                lexical_match = comparison.lexical_match_percentage
                if lexical_match is not None:
                    components.append(lexical_match)

        speaking_score = sum(components) / len(components) if components else None

        needs_review = False
        if is_failed:
            needs_review = True
        elif speaking_score is not None and speaking_score < 70:
            needs_review = True
        elif lexical_match is not None and lexical_match < 70:
            needs_review = True

        return (speaking_score, needs_review, is_failed)

    @staticmethod
    def _determine_intervention_level(
        final_score: float,
        review_required_count: int,
        any_failed: bool,
        writing_review_required_count: int = 0,
    ) -> InterventionLevel:
        if any_failed:
            return InterventionLevel.HIGH
        if final_score >= 80:
            if review_required_count > 0:
                return InterventionLevel.MEDIUM
            return InterventionLevel.LOW
        elif final_score >= 50:
            level = InterventionLevel.MEDIUM
        else:
            return InterventionLevel.HIGH

        # Extra elevation for writing reviews: if MEDIUM and final_score < 70,
        # elevate to HIGH when writing reviews are present.
        if writing_review_required_count > 0 and final_score < 70:
            return InterventionLevel.HIGH
        return level
