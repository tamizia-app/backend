from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.school.application.assemblers.student_assembler import StudentConsentAssembler
from app.school.application.exceptions.student_exceptions import ConsentAlreadyRevokedError, StudentConsentNotFoundError, StudentNotFoundError
from app.school.application.ports.blob_storage import BlobStorage
from app.school.application.ports.consent_repository import StudentConsentRepository
from app.school.application.ports.student_repository import StudentRepository
from app.school.application.results.student_result import StudentConsentResult
from app.school.infrastructure.adapters.pdf_watermark import watermark_pdf
from app.school.domain.student import StudentConsent


def _extract_version(blob_path: str | None) -> int:
    if not blob_path:
        return 0
    try:
        parts = blob_path.rstrip("/").split("_")
        return int(parts[-1])
    except (ValueError, IndexError):
        return 0


@dataclass
class RevokeConsentCommand:
    student_id: UUID
    teacher_id: UUID
    classroom_id: UUID


class RevokeConsentUseCase:
    def __init__(self, student_repo: StudentRepository, consent_repo: StudentConsentRepository, blob_storage: BlobStorage) -> None:
        self._student_repo = student_repo
        self._consent_repo = consent_repo
        self._blob_storage = blob_storage

    def execute(self, command: RevokeConsentCommand) -> StudentConsentResult:
        student = self._student_repo.find_by_id(command.student_id)
        if not student:
            raise StudentNotFoundError()

        existing = self._consent_repo.find_by_student_id(command.student_id)
        if not existing:
            raise StudentConsentNotFoundError()
        if existing.revoked_at is not None:
            raise ConsentAlreadyRevokedError()

        original_content = self._blob_storage.get_content(blob_path=existing.evidence_blob_path)

        next_version = _extract_version(existing.evidence_blob_path) + 1
        content = watermark_pdf(original_content)
        blob_path = self._blob_storage.upload_pdf(
            content=content,
            teacher_id=command.teacher_id,
            classroom_id=command.classroom_id,
            student_id=command.student_id,
            version=next_version,
        )

        now = datetime.now(timezone.utc)
        updated = self._consent_repo.update(
            StudentConsent(
                id=existing.id,
                student_id=existing.student_id,
                status=False,
                consent_date=existing.consent_date,
                revoked_at=now,
                evidence_blob_path=blob_path,
                created_at=existing.created_at,
                updated_at=now,
            )
        )

        return StudentConsentAssembler.to_result(updated)
