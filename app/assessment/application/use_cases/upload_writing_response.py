from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.assemblers import WritingResponseAssembler
from app.assessment.application.exceptions import (
    ExerciseAttemptNotFoundError,
    InvalidExerciseTypeError,
)
from app.assessment.application.ports.blob_storage import AssessmentBlobStorage
from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentRepository,
    ExerciseAttemptRepository,
    ExerciseRepository,
    TemplateExerciseRepository,
    WritingMetricsRepository,
    WritingResponseRepository,
)
from app.assessment.application.results import WritingResponseResult
from app.assessment.domain.enums import ExerciseAttemptStatus, ExerciseType
from app.assessment.domain.metrics import WritingMetrics
from app.assessment.domain.response import WritingResponse


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
    ) -> None:
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._assessment_attempt_repo = assessment_attempt_repo
        self._assessment_repo = assessment_repo
        self._writing_response_repo = writing_response_repo
        self._writing_metrics_repo = writing_metrics_repo
        self._blob_storage = blob_storage

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
        assessment = self._assessment_repo.find_by_id(attempt.assessment_id)

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
        if existing:
            response = self._writing_response_repo.update(
                WritingResponse(
                    id=existing.id,
                    exercise_attempt_id=command.exercise_attempt_id,
                    image_blob_path=blob_path,
                    original_filename=command.original_filename,
                    content_type=command.content_type,
                    recognized_text=existing.recognized_text,
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
                    recognized_text=None,
                    strokes_json=strokes,
                    canvas_metadata_json=canvas_meta,
                    input_metadata_json=input_meta,
                    frontend_metrics_json=frontend_metrics,
                    created_at=now,
                    updated_at=now,
                )
            )

        if frontend_metrics:
            metrics_data = self._extract_metrics(frontend_metrics)
            existing_metrics = self._writing_metrics_repo.find_by_writing_response_id(response.id)
            if existing_metrics:
                self._writing_metrics_repo.update(
                    WritingMetrics(
                        id=existing_metrics.id,
                        writing_response_id=response.id,
                        created_at=existing_metrics.created_at,
                        updated_at=now,
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
                        **metrics_data,
                    )
                )

        # Mark exercise attempt as ANSWERED (not EVALUATED until OCR is done)
        ea.status = ExerciseAttemptStatus.ANSWERED
        ea.submitted_at = now
        self._exercise_attempt_repo.update(ea)

        return WritingResponseAssembler.to_result(response)

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
