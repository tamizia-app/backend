from dataclasses import dataclass
from uuid import UUID

from app.assessment.application.assemblers import FinalResultAssembler
from app.assessment.application.exceptions import AttemptNotFoundError
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
from app.assessment.application.results import FinalResult
from app.assessment.domain.enums import ExerciseAttemptStatus, ExerciseType
from app.assessment.domain.text_comparison import compare_texts


@dataclass
class GetAssessmentResultQuery:
    attempt_id: UUID


class GetAssessmentResultUseCase:
    def __init__(
        self,
        attempt_repo: AssessmentAttemptRepository,
        result_repo: AssessmentResultRepository,
        exercise_attempt_repo: ExerciseAttemptRepository | None = None,
        template_exercise_repo: TemplateExerciseRepository | None = None,
        exercise_repo: ExerciseRepository | None = None,
        mc_response_repo: MCResponseRepository | None = None,
        os_response_repo: OSResponseRepository | None = None,
        speaking_response_repo: SpeakingResponseRepository | None = None,
        writing_response_repo: WritingResponseRepository | None = None,
        writing_metrics_repo: WritingMetricsRepository | None = None,
        speaking_metrics_repo: SpeakingMetricsRepository | None = None,
        prompt_exercise_repo: PromptExerciseRepository | None = None,
        expected_answer_repo: ExpectedAnswerRepository | None = None,
    ) -> None:
        self._attempt_repo = attempt_repo
        self._result_repo = result_repo
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._mc_response_repo = mc_response_repo
        self._os_response_repo = os_response_repo
        self._speaking_response_repo = speaking_response_repo
        self._writing_response_repo = writing_response_repo
        self._writing_metrics_repo = writing_metrics_repo
        self._speaking_metrics_repo = speaking_metrics_repo
        self._prompt_exercise_repo = prompt_exercise_repo
        self._expected_answer_repo = expected_answer_repo

    def execute(self, query: GetAssessmentResultQuery) -> FinalResult:
        attempt = self._attempt_repo.find_by_id(query.attempt_id)
        if not attempt:
            raise AttemptNotFoundError()

        result = self._result_repo.find_by_attempt_id(query.attempt_id)
        if not result:
            raise AttemptNotFoundError("Result not yet generated. Finish the attempt first.")

        if self._exercise_attempt_repo:
            result = self._recalculate_computed_fields(result, query.attempt_id)

        return FinalResultAssembler.to_result(result)

    def _recalculate_computed_fields(self, result, attempt_id):
        exercise_attempts = self._exercise_attempt_repo.find_by_assessment_attempt_id(attempt_id)

        total_exercises = 0
        evaluated_exercises = 0
        review_required_count = 0
        speaking_scores = []
        writing_scores = []
        writing_review_count = 0

        for ea in exercise_attempts:
            te = self._template_exercise_repo.find_by_id(ea.template_exercise_id)
            exercise = self._exercise_repo.find_by_id(te.exercise_id)
            total_exercises += 1

            if ea.status == ExerciseAttemptStatus.PENDING:
                continue

            evaluated_exercises += 1
            etype = exercise.type

            if etype in (ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING):
                speaking_resp = self._speaking_response_repo.find_by_exercise_attempt_id(ea.id)
                if speaking_resp:
                    score, needs_review, _ = self._evaluate_speaking(exercise.id, speaking_resp)
                    if score is not None:
                        speaking_scores.append(score)
                    if needs_review:
                        review_required_count += 1

            elif etype in (ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING):
                wr = self._writing_response_repo.find_by_exercise_attempt_id(ea.id)
                if wr and self._writing_metrics_repo:
                    metrics = self._writing_metrics_repo.find_by_writing_response_id(wr.id)
                    if metrics and metrics.similarity_score is not None:
                        writing_scores.append(metrics.similarity_score)
                        if metrics.similarity_score < 75:
                            writing_review_count += 1

        result.total_exercises = total_exercises
        result.evaluated_exercises = evaluated_exercises
        result.pending_exercises = total_exercises - evaluated_exercises
        result.speaking_average_score = (
            sum(speaking_scores) / len(speaking_scores) if speaking_scores else None
        )
        result.speaking_review_required_count = review_required_count
        result.writing_average_score = (
            sum(writing_scores) / len(writing_scores) if writing_scores else None
        )
        result.writing_review_required_count = writing_review_count
        return result

    def _evaluate_speaking(self, exercise_id, speaking_resp):
        metrics = self._speaking_metrics_repo.find_by_speaking_response_id(speaking_resp.id)
        if metrics is None:
            return (None, True, True)

        components = []
        if metrics.pronunciation_score is not None:
            components.append(metrics.pronunciation_score)
        if metrics.accuracy_score is not None:
            components.append(metrics.accuracy_score)
        if metrics.completeness_score is not None:
            components.append(metrics.completeness_score)

        lexical_match = None
        prompt_exercise = self._prompt_exercise_repo.find_by_exercise_id(exercise_id)
        if prompt_exercise:
            expected_answer = self._expected_answer_repo.find_by_prompt_exercise_id(
                prompt_exercise.id
            )
            if expected_answer and speaking_resp.free_transcription_text:
                comparison = compare_texts(
                    expected_answer.expected_text, speaking_resp.free_transcription_text
                )
                lexical_match = comparison.lexical_match_percentage
                if lexical_match is not None:
                    components.append(lexical_match)

        speaking_score = sum(components) / len(components) if components else None
        needs_review = False
        if speaking_score is not None and speaking_score < 70:
            needs_review = True
        elif lexical_match is not None and lexical_match < 70:
            needs_review = True

        return (speaking_score, needs_review, False)
