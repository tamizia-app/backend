from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.assemblers import WritingResponseAssembler
from app.assessment.application.exceptions import (
    AttemptAlreadyCompletedError,
    ExerciseAttemptNotFoundError,
    InvalidExerciseTypeError,
)
from app.assessment.application.ports.blob_storage import AssessmentBlobStorage
from app.assessment.application.ports.ocr_service import OcrResult, OcrService
from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentRepository,
    ExerciseAttemptRepository,
    ExerciseScoreRepository,
    ExerciseRepository,
    ExpectedAnswerRepository,
    PromptExerciseRepository,
    TemplateExerciseRepository,
    WritingMetricsRepository,
    WritingResponseRepository,
)
from app.assessment.application.results import WritingResponseResult
from app.assessment.application.exercise_score_service import persist_exercise_score
from app.assessment.domain.writing_text_comparison import determine_writing_review
from app.assessment.domain.enums import AttemptStatus, ExerciseAttemptStatus, ExerciseType
from app.assessment.domain.file_validation import validate_image_content
from app.assessment.domain.metrics import WritingMetrics
from app.assessment.domain.response import WritingResponse
from app.assessment.domain.technical_quality import writing_quality


@dataclass
class UploadWritingResponseCommand:
    exercise_attempt_id: UUID
    file_content: bytes
    original_filename: str
    content_type: str
    payload_json: dict | None = None


class UploadWritingResponseUseCase:
    def __init__(
        self,
        exercise_attempt_repo: ExerciseAttemptRepository,
        template_exercise_repo: TemplateExerciseRepository,
        exercise_repo: ExerciseRepository,
        assessment_attempt_repo: AssessmentAttemptRepository,
        assessment_repo: AssessmentRepository,
        writing_response_repo: WritingResponseRepository,
        writing_metrics_repo: WritingMetricsRepository,
        blob_storage: AssessmentBlobStorage,
        ocr_service: OcrService | None = None,
        prompt_exercise_repo: PromptExerciseRepository | None = None,
        expected_answer_repo: ExpectedAnswerRepository | None = None,
        exercise_score_repo: ExerciseScoreRepository | None = None,
    ) -> None:
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._assessment_attempt_repo = assessment_attempt_repo
        self._assessment_repo = assessment_repo
        self._writing_response_repo = writing_response_repo
        self._writing_metrics_repo = writing_metrics_repo
        self._blob_storage = blob_storage
        self._ocr_service = ocr_service
        self._prompt_exercise_repo = prompt_exercise_repo
        self._expected_answer_repo = expected_answer_repo
        self._exercise_score_repo = exercise_score_repo

    def execute(self, command: UploadWritingResponseCommand) -> WritingResponseResult:
        ea = self._exercise_attempt_repo.find_by_id(command.exercise_attempt_id)
        if not ea:
            raise ExerciseAttemptNotFoundError()

        te = self._template_exercise_repo.find_by_id(ea.template_exercise_id)
        exercise = self._exercise_repo.find_by_id(te.exercise_id)
        if exercise.type not in (ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING):
            raise InvalidExerciseTypeError(
                "Exercise is not a writing type. Use the correct response endpoint."
            )

        attempt = self._assessment_attempt_repo.find_by_id(ea.assessment_attempt_id)
        if attempt.status == AttemptStatus.COMPLETED:
            raise AttemptAlreadyCompletedError("Completed attempts are immutable. Create a repeat attempt.")
        assessment = self._assessment_repo.find_by_id(attempt.assessment_id)

        image_valid, image_error = validate_image_content(
            command.file_content, command.content_type
        )

        ext = command.original_filename.rsplit(".", 1)[-1] if "." in command.original_filename else "png"
        blob_path = self._blob_storage.upload_file(
            content=command.file_content,
            content_type=command.content_type,
            teacher_id=assessment.homeroom_teacher_id,
            classroom_id=assessment.classroom_id,
            student_id=attempt.student_id,
            assessment_attempt_id=attempt.id,
            exercise_attempt_id=command.exercise_attempt_id,
            subfolder="writing",
            filename=f"image.{ext}",
        )

        now = datetime.now(timezone.utc)

        payload = command.payload_json or {}
        strokes = payload.get("strokes")
        canvas_meta = payload.get("canvas")
        input_meta = payload.get("input")
        frontend_metrics = payload.get("metrics")

        existing = self._writing_response_repo.find_by_exercise_attempt_id(command.exercise_attempt_id)

        # Run OCR on the uploaded image
        ocr_result: OcrResult | None = None
        recognized_text: str | None = None
        if self._ocr_service is not None:
            ocr_result = self._ocr_service.extract_text(command.file_content)
            if ocr_result.full_text:
                recognized_text = ocr_result.full_text
        if existing:
            response = self._writing_response_repo.update(
                WritingResponse(
                    id=existing.id,
                    exercise_attempt_id=command.exercise_attempt_id,
                    image_blob_path=blob_path,
                    original_filename=command.original_filename,
                    content_type=command.content_type,
                    recognized_text=recognized_text,
                    strokes_json=strokes,
                    canvas_metadata_json=canvas_meta,
                    input_metadata_json=input_meta,
                    frontend_metrics_json=frontend_metrics,
                    created_at=existing.created_at,
                    updated_at=now,
                )
            )
        else:
            response = self._writing_response_repo.create(
                WritingResponse(
                    id=UUID(int=0),
                    exercise_attempt_id=command.exercise_attempt_id,
                    image_blob_path=blob_path,
                    original_filename=command.original_filename,
                    content_type=command.content_type,
                    recognized_text=recognized_text,
                    strokes_json=strokes,
                    canvas_metadata_json=canvas_meta,
                    input_metadata_json=input_meta,
                    frontend_metrics_json=frontend_metrics,
                    created_at=now,
                    updated_at=now,
                )
            )

        ocr_metrics = {}
        if ocr_result and ocr_result.full_text:
            ocr_metrics["confidence_avg"] = ocr_result.confidence_avg
            ocr_metrics["raw_ocr_result_json"] = ocr_result.raw_response

        # Run text comparison if we have both expected and recognized text
        expected_text = self._get_expected_text(te)
        review = determine_writing_review(
            expected=expected_text or "",
            recognized=recognized_text or "",
            confidence_avg=ocr_result.confidence_avg if ocr_result else None,
        )
        candidate_score = review.similarity_score if expected_text and recognized_text else None
        if expected_text and recognized_text:
            ocr_metrics["cer"] = review.cer
            ocr_metrics["wer"] = review.wer
            ocr_metrics["similarity_score"] = review.similarity_score

        if frontend_metrics or ocr_metrics or ocr_result or image_error:
            metrics_data = self._extract_metrics(frontend_metrics or {})
            metrics_data.update(ocr_metrics)
            existing_metrics = self._writing_metrics_repo.find_by_writing_response_id(response.id)
            if existing_metrics:
                self._writing_metrics_repo.update(
                    WritingMetrics(
                        id=existing_metrics.id,
                        writing_response_id=response.id,
                        created_at=existing_metrics.created_at,
                        updated_at=now,
                        review_json={
                            "required": review.review_required,
                            "reasons": review.review_reasons,
                        },
                        quality_json=None,
                        original_char_accuracy=(
                            existing_metrics.original_char_accuracy
                            if existing_metrics.original_char_accuracy is not None
                            else review.char_accuracy
                            if expected_text and recognized_text
                            else None
                        ),
                        current_char_accuracy=review.char_accuracy if expected_text and recognized_text else None,
                        original_word_accuracy=(
                            existing_metrics.original_word_accuracy
                            if existing_metrics.original_word_accuracy is not None
                            else review.word_accuracy
                            if expected_text and recognized_text
                            else None
                        ),
                        current_word_accuracy=review.word_accuracy if expected_text and recognized_text else None,
                        original_similarity_score=(
                            existing_metrics.original_similarity_score
                            if existing_metrics.original_similarity_score is not None
                            else candidate_score
                        ),
                        current_similarity_score=candidate_score,
                        **metrics_data,
                    )
                )
            else:
                self._writing_metrics_repo.create(
                    WritingMetrics(
                        id=UUID(int=0),
                        writing_response_id=response.id,
                        created_at=now,
                        updated_at=now,
                        review_json={
                            "required": review.review_required,
                            "reasons": review.review_reasons,
                        },
                        quality_json=None,
                        original_char_accuracy=review.char_accuracy if expected_text and recognized_text else None,
                        current_char_accuracy=review.char_accuracy if expected_text and recognized_text else None,
                        original_word_accuracy=review.word_accuracy if expected_text and recognized_text else None,
                        current_word_accuracy=review.word_accuracy if expected_text and recognized_text else None,
                        original_similarity_score=candidate_score,
                        current_similarity_score=candidate_score,
                        **metrics_data,
                    )
                )

        quality_reasons = list(review.review_reasons)
        successful_ocr = bool(ocr_result and ocr_result.full_text)
        if image_error and not successful_ocr:
            quality_reasons.append(image_error)
        quality = writing_quality(
            recognized_text=recognized_text,
            confidence_avg=ocr_result.confidence_avg if ocr_result else None,
            score=candidate_score,
            review_required=review.review_required or bool(image_error),
            review_reasons=quality_reasons,
            error_code=(
                ocr_result.error_code
                if ocr_result and ocr_result.error_code
                else image_error
                if image_error and not successful_ocr
                else None
            ),
        )
        existing_metrics = self._writing_metrics_repo.find_by_writing_response_id(response.id)
        if existing_metrics:
            existing_metrics.quality_json = quality.to_dict()
            self._writing_metrics_repo.update(existing_metrics)
        scoring_components = {
            "formula_version": "phase2_v1",
            "formula": "0.75_char_accuracy + 0.25_word_accuracy",
            "component_weights": {
                "char_accuracy": 0.75,
                "word_accuracy": 0.25,
            },
            "confidence_avg": ocr_result.confidence_avg if ocr_result else None,
            "cer": review.cer if expected_text else None,
            "wer": review.wer if expected_text else None,
            "similarity_score": candidate_score,
            "char_accuracy": review.char_accuracy if expected_text else None,
            "word_accuracy": review.word_accuracy if expected_text else None,
        }
        if self._exercise_score_repo:
            persist_exercise_score(
                self._exercise_score_repo,
                exercise_attempt_id=ea.id,
                exercise_type=exercise.type,
                score=candidate_score,
                quality=quality,
                scoring_components=scoring_components,
            )

        ea.status = (
            ExerciseAttemptStatus.EVALUATED
            if quality.score_eligible
            else ExerciseAttemptStatus.FAILED
            if quality.technical_status.value == "INVALID"
            else ExerciseAttemptStatus.ANSWERED
        )
        ea.submitted_at = now
        self._exercise_attempt_repo.update(ea)

        result = WritingResponseAssembler.to_result(response)
        result.metrics = {
            **scoring_components,
            "review_required": quality.manual_review_required,
            "review_reasons": quality.quality_reasons,
        }
        result.exercise_score = candidate_score
        result.technical_status = quality.technical_status.value
        result.score_eligible = quality.score_eligible
        result.manual_review_required = quality.manual_review_required
        result.quality_reasons = quality.quality_reasons
        result.scoring_components = scoring_components
        return result

    def _get_expected_text(self, te) -> str | None:
        if not self._prompt_exercise_repo or not self._expected_answer_repo:
            return None
        prompt = self._prompt_exercise_repo.find_by_exercise_id(te.exercise_id)
        if not prompt:
            return None
        answer = self._expected_answer_repo.find_by_prompt_exercise_id(prompt.id)
        if not answer:
            return None
        return answer.expected_text

    @staticmethod
    def _extract_metrics(m: dict) -> dict:
        return {
            "duration_ms": m.get("duration_ms"),
            "stroke_count": m.get("stroke_count"),
            "point_count": m.get("point_count"),
            "average_speed": m.get("average_speed"),
            "speed_variability": m.get("speed_variability"),
            "pause_count": m.get("pause_count"),
            "longest_pause_ms": m.get("longest_pause_ms"),
            "total_pause_time_ms": m.get("total_pause_time_ms"),
            "pressure_min": m.get("pressure_min"),
            "pressure_max": m.get("pressure_max"),
            "pressure_avg": m.get("pressure_avg"),
            "bounding_box_json": m.get("bounding_box"),
            "writing_area_usage": m.get("writing_area_usage"),
        }
