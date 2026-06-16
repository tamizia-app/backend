from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.enums import SessionStatus
from app.assessment.modules.evidences.domain.entities import EvidenceFile, WritingEvidenceMetadata
from app.assessment.modules.evidences.domain.exceptions import SessionClosedForEvidenceError
from app.assessment.modules.evidences.domain.repositories import EvidenceRepository, EvidenceStorage


@dataclass(frozen=True)
class UploadWritingEvidenceCommand:
    session: Any
    current_user: Any
    file: EvidenceFile
    metadata: WritingEvidenceMetadata


class UploadWritingEvidenceUseCase:
    def __init__(self, repository: EvidenceRepository, storage: EvidenceStorage) -> None:
        self.repository = repository
        self.storage = storage

    def execute(self, command: UploadWritingEvidenceCommand):
        if command.session.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
            raise SessionClosedForEvidenceError()

        image_url = self.storage.upload_bytes(
            content=command.file.content,
            folder="writing-samples",
            filename=command.file.filename,
            content_type=command.file.content_type,
        )
        self.repository.clear_writing_analysis_and_result(command.session)
        sample = self.repository.create_or_update_writing_sample(
            session=command.session,
            image_url=image_url,
            source_type=command.metadata.source_type,
            stroke_count=command.metadata.stroke_count,
            correction_count=command.metadata.correction_count,
            duration_seconds=command.metadata.duration_seconds,
        )
        self.repository.add(sample)
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="upload_writing_sample",
            entity_type="writing_sample",
            entity_id=sample.id,
        )
        return sample

