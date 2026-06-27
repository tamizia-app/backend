from typing import Protocol
from uuid import UUID


class AssessmentBlobStorage(Protocol):
    def upload_file(
        self,
        *,
        content: bytes,
        content_type: str,
        teacher_id: UUID,
        classroom_id: UUID,
        student_id: UUID,
        assessment_attempt_id: UUID,
        exercise_attempt_id: UUID,
        subfolder: str,
        filename: str,
    ) -> str: ...

    def download_url(self, *, blob_path: str) -> str: ...
