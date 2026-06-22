from dataclasses import dataclass
from uuid import UUID

from app.school.application.exceptions.student_exceptions import StudentConsentNotFoundError, StudentNotFoundError
from app.school.application.ports.blob_storage import BlobStorage
from app.school.application.ports.consent_repository import StudentConsentRepository
from app.school.application.ports.student_repository import StudentRepository


@dataclass
class DownloadConsentQuery:
    student_id: UUID


class DownloadConsentUseCase:
    def __init__(self, student_repo: StudentRepository, consent_repo: StudentConsentRepository, blob_storage: BlobStorage) -> None:
        self._student_repo = student_repo
        self._consent_repo = consent_repo
        self._blob_storage = blob_storage

    def execute(self, query: DownloadConsentQuery) -> str:
        student = self._student_repo.find_by_id(query.student_id)
        if not student:
            raise StudentNotFoundError()

        consent = self._consent_repo.find_by_student_id(query.student_id)
        if not consent or not consent.evidence_blob_path:
            raise StudentConsentNotFoundError()

        return self._blob_storage.download_url(blob_path=consent.evidence_blob_path)
