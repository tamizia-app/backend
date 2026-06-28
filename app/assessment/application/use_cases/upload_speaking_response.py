from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.assemblers import SpeakingResponseAssembler
from app.assessment.application.exceptions import (
    ExerciseAttemptNotFoundError,
    ExpectedTextNotFoundError,
    InvalidExerciseTypeError,
)
from app.assessment.application.ports.blob_storage import AssessmentBlobStorage
from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentRepository,
    ExerciseAttemptRepository,
    ExerciseRepository,
    ExpectedAnswerRepository,
    PromptExerciseRepository,
    SpeakingMetricsRepository,
    SpeakingResponseRepository,
    TemplateExerciseRepository,
)
from app.assessment.application.results import SpeakingResponseResult
from app.assessment.application.use_cases.assess_reading_pipeline import (
    AssessReadingCommand,
    AssessReadingPipelineUseCase,
)
from app.assessment.domain.enums import ExerciseAttemptStatus, ExerciseType
from app.assessment.domain.metrics import SpeakingMetrics
from app.assessment.domain.response import SpeakingResponse

DEFAULT_ASSESSMENT_LOCALE = "es-PE"


@dataclass
class UploadSpeakingResponseCommand:
    exercise_attempt_id: UUID
    file_content: bytes
    original_filename: str
    content_type: str
    duration_ms: int | None


class UploadSpeakingResponseUseCase:
    def __init__(
        self,
        exercise_attempt_repo: ExerciseAttemptRepository,
        template_exercise_repo: TemplateExerciseRepository,
        exercise_repo: ExerciseRepository,
        assessment_attempt_repo: AssessmentAttemptRepository,
        assessment_repo: AssessmentRepository,
        speaking_response_repo: SpeakingResponseRepository,
        speaking_metrics_repo: SpeakingMetricsRepository,
        prompt_exercise_repo: PromptExerciseRepository,
        expected_answer_repo: ExpectedAnswerRepository,
        blob_storage: AssessmentBlobStorage,
        pipeline: AssessReadingPipelineUseCase,
    ) -> None:
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._assessment_attempt_repo = assessment_attempt_repo
        self._assessment_repo = assessment_repo
        self._speaking_response_repo = speaking_response_repo
        self._speaking_metrics_repo = speaking_metrics_repo
        self._prompt_exercise_repo = prompt_exercise_repo
        self._expected_answer_repo = expected_answer_repo
        self._blob_storage = blob_storage
        self._pipeline = pipeline

    async def execute(self, command: UploadSpeakingResponseCommand) -> SpeakingResponseResult:
        ea = self._exercise_attempt_repo.find_by_id(command.exercise_attempt_id)
        if not ea:
            raise ExerciseAttemptNotFoundError()

        te = self._template_exercise_repo.find_by_id(ea.template_exercise_id)
        exercise = self._exercise_repo.find_by_id(te.exercise_id)
        if exercise.type not in (ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING):
            raise InvalidExerciseTypeError(
                "Exercise is not a speaking type. Use the correct response endpoint."
            )

        prompt_exercise = self._prompt_exercise_repo.find_by_exercise_id(exercise.id)
        if not prompt_exercise:
            raise ExpectedTextNotFoundError("No prompt exercise found for this exercise.")

        expected_answer = self._expected_answer_repo.find_by_prompt_exercise_id(prompt_exercise.id)
        if not expected_answer or not expected_answer.expected_text.strip():
            raise ExpectedTextNotFoundError("Expected text not found for this exercise.")

        attempt = self._assessment_attempt_repo.find_by_id(ea.assessment_attempt_id)
        assessment = self._assessment_repo.find_by_id(attempt.assessment_id)

        ext = command.original_filename.rsplit(".", 1)[-1] if "." in command.original_filename else "bin"
        blob_path = self._blob_storage.upload_file(
            content=command.file_content,
            content_type=command.content_type,
            teacher_id=assessment.homeroom_teacher_id,
            classroom_id=assessment.classroom_id,
            student_id=attempt.student_id,
            assessment_attempt_id=attempt.id,
            exercise_attempt_id=command.exercise_attempt_id,
            subfolder="speaking",
            filename=f"audio.{ext}",
        )

        language_code = prompt_exercise.language_code or DEFAULT_ASSESSMENT_LOCALE
        pipeline_result = await self._pipeline.execute(
            AssessReadingCommand(
                audio_content=command.file_content,
                expected_text=expected_answer.expected_text,
                assessment_locale=language_code,
                audio_format=command.content_type,
            )
        )

        evaluation_status: str = pipeline_result.get("status", "failed")
        free_text: str | None = pipeline_result.get("recognized_text") or pipeline_result.get("stt_recognized_text")
        azure_text: str | None = pipeline_result.get("assessment_recognized_text")

        pronunciation_score: float | None = pipeline_result.get("pronunciation_score")
        accuracy_score: float | None = pipeline_result.get("accuracy_score")
        fluency_score: float | None = pipeline_result.get("fluency_score")
        completeness_score: float | None = pipeline_result.get("completeness_score")
        prosody_score: float | None = pipeline_result.get("prosody_score")

        duration_ms: int | None = pipeline_result.get("duration_ms") or command.duration_ms

        now = datetime.now(timezone.utc)
        existing = self._speaking_response_repo.find_by_exercise_attempt_id(command.exercise_attempt_id)
        if existing:
            response = self._speaking_response_repo.update(
                SpeakingResponse(
                    id=existing.id,
                    exercise_attempt_id=command.exercise_attempt_id,
                    audio_blob_path=blob_path,
                    original_filename=command.original_filename,
                    content_type=command.content_type,
                    duration_ms=duration_ms,
                    recognized_text=free_text,
                    free_transcription_text=free_text,
                    assessment_recognized_text=azure_text,
                    created_at=existing.created_at,
                    updated_at=now,
                )
            )
        else:
            response = self._speaking_response_repo.create(
                SpeakingResponse(
                    id=UUID(int=0),
                    exercise_attempt_id=command.exercise_attempt_id,
                    audio_blob_path=blob_path,
                    original_filename=command.original_filename,
                    content_type=command.content_type,
                    duration_ms=duration_ms,
                    recognized_text=free_text,
                    free_transcription_text=free_text,
                    assessment_recognized_text=azure_text,
                    created_at=now,
                    updated_at=now,
                )
            )

        raw_speech: dict | None = pipeline_result.get("raw_result_json")
        raw_stt: dict | None = pipeline_result.get("stt")
        transcription_export: dict | None = None
        if raw_stt and isinstance(raw_stt, dict):
            export: dict = {}
            for key in ("text", "language", "segments", "words", "duration_ms"):
                if key in raw_stt:
                    export[key] = raw_stt[key]
            transcription_export = export or raw_stt

        existing_metrics = self._speaking_metrics_repo.find_by_speaking_response_id(response.id)
        if existing_metrics:
            self._speaking_metrics_repo.update(
                SpeakingMetrics(
                    id=existing_metrics.id,
                    speaking_response_id=response.id,
                    pronunciation_score=pronunciation_score,
                    accuracy_score=accuracy_score,
                    fluency_score=fluency_score,
                    completeness_score=completeness_score,
                    prosody_score=prosody_score,
                    raw_speech_result_json=raw_speech,
                    raw_transcription_result_json=transcription_export,
                    created_at=existing_metrics.created_at,
                    updated_at=now,
                )
            )
        else:
            self._speaking_metrics_repo.create(
                SpeakingMetrics(
                    id=UUID(int=0),
                    speaking_response_id=response.id,
                    pronunciation_score=pronunciation_score,
                    accuracy_score=accuracy_score,
                    fluency_score=fluency_score,
                    completeness_score=completeness_score,
                    prosody_score=prosody_score,
                    raw_speech_result_json=raw_speech,
                    raw_transcription_result_json=transcription_export,
                    created_at=now,
                    updated_at=now,
                )
            )

        if evaluation_status == "completed":
            ea.status = ExerciseAttemptStatus.EVALUATED
        elif evaluation_status == "partial":
            ea.status = ExerciseAttemptStatus.ANSWERED
        else:
            ea.status = ExerciseAttemptStatus.FAILED
        ea.submitted_at = now
        self._exercise_attempt_repo.update(ea)

        return SpeakingResponseResult(
            response_id=response.id,
            exercise_attempt_id=command.exercise_attempt_id,
            audio_blob_path=blob_path,
            original_filename=command.original_filename,
            content_type=command.content_type,
            duration_ms=duration_ms,
            free_transcription_text=free_text,
            assessment_recognized_text=azure_text,
            recognized_text=free_text,
            pronunciation_score=pronunciation_score,
            accuracy_score=accuracy_score,
            fluency_score=fluency_score,
            completeness_score=completeness_score,
            prosody_score=prosody_score,
            evaluation_status=evaluation_status,
            comparison=pipeline_result.get("comparison"),
            review=pipeline_result.get("review"),
            error_message=pipeline_result.get("error_message"),
        )
