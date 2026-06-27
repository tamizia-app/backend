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
    WritingResponseRepository,
)
from app.assessment.application.results import WritingResponseResult
from app.assessment.domain.enums import ExerciseType
from app.assessment.domain.response import WritingResponse


@dataclass
class UploadWritingResponseCommand:
    exercise_attempt_id: UUID
    file_content: bytes
    original_filename: str
    content_type: str


class UploadWritingResponseUseCase:
    def __init__(
        self,
        exercise_attempt_repo: ExerciseAttemptRepository,
        template_exercise_repo: TemplateExerciseRepository,
        exercise_repo: ExerciseRepository,
        assessment_attempt_repo: AssessmentAttemptRepository,
        assessment_repo: AssessmentRepository,
        writing_response_repo: WritingResponseRepository,
        blob_storage: AssessmentBlobStorage,
    ) -> None:
        self._exercise_attempt_repo = exercise_attempt_repo
        self._template_exercise_repo = template_exercise_repo
        self._exercise_repo = exercise_repo
        self._assessment_attempt_repo = assessment_attempt_repo
        self._assessment_repo = assessment_repo
        self._writing_response_repo = writing_response_repo
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
                    created_at=now,
                    updated_at=now,
                )
            )

        return WritingResponseAssembler.to_result(response)
