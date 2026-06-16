from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.enums import SessionStatus
from app.assessment.modules.evidences.domain.entities import WritingEvidenceMetadata
from app.assessment.modules.evidences.domain.exceptions import SessionClosedForEvidenceError
from app.assessment.modules.evidences.domain.repositories import EvidenceRepository


@dataclass(frozen=True)
class RegisterWritingMetadataCommand:
    writing_sample: Any
    session: Any
    current_user: Any
    metadata: WritingEvidenceMetadata


class RegisterWritingMetadataUseCase:
    def __init__(self, repository: EvidenceRepository) -> None:
        self.repository = repository

    def execute(self, command: RegisterWritingMetadataCommand):
        if command.session.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
            raise SessionClosedForEvidenceError()

        command.writing_sample.source_type = command.metadata.source_type
        command.writing_sample.stroke_count = command.metadata.stroke_count
        command.writing_sample.correction_count = command.metadata.correction_count
        command.writing_sample.duration_seconds = command.metadata.duration_seconds
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="update_writing_metadata",
            entity_type="writing_sample",
            entity_id=command.writing_sample.id,
        )
        return command.writing_sample
