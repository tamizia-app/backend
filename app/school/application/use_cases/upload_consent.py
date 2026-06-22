from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.school.application.assemblers.student_assembler import StudentConsentAssembler
from app.school.application.exceptions.student_exceptions import StudentNotFoundError
from app.school.application.ports.blob_storage import BlobStorage
from app.school.application.ports.consent_repository import StudentConsentRepository
from app.school.application.ports.student_repository import StudentRepository
from app.school.application.results.student_result import StudentConsentResult
from app.school.application.use_cases.revoke_consent import _extract_version
from app.school.domain.student import StudentConsent


@dataclass
class UploadConsentCommand:
    student_id: UUID
    teacher_id: UUID
    classroom_id: UUID
    content: bytes


class UploadConsentUseCase:
    def __init__(self, student_repo: StudentRepository, consent_repo: StudentConsentRepository, blob_storage: BlobStorage) -> None:
        self._student_repo = student_repo
        self._consent_repo = consent_repo
        self._blob_storage = blob_storage

    def execute(self, command: UploadConsentCommand) -> StudentConsentResult:
        student = self._student_repo.find_by_id(command.student_id)
        if not student:
            raise StudentNotFoundError()

        existing = self._consent_repo.find_by_student_id(command.student_id)
        next_version = _extract_version(existing.evidence_blob_path) + 1 if existing else 1

        blob_path = self._blob_storage.upload_pdf(
            content=command.content,
            teacher_id=command.teacher_id,
            classroom_id=command.classroom_id,
            student_id=command.student_id,
            version=next_version,
        )

        now = datetime.now(timezone.utc)
        if existing:
            updated = self._consent_repo.update(
                StudentConsent(
                    id=existing.id,
                    student_id=existing.student_id,
                    status=True,
                    consent_date=existing.consent_date or now,
                    revoked_at=None,
                    evidence_blob_path=blob_path,
                    created_at=existing.created_at,
                    updated_at=now,
                )
            )
        else:
            updated = self._consent_repo.create(
                StudentConsent(
                    id=UUID(int=0),
                    student_id=command.student_id,
                    status=True,
                    consent_date=now,
                    revoked_at=None,
                    evidence_blob_path=blob_path,
                    created_at=now,
                    updated_at=now,
                )
            )

        return StudentConsentAssembler.to_result(updated)
