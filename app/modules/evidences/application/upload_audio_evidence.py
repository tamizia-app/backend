from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.enums import SessionStatus
from app.modules.evidences.domain.entities import AudioEvidenceMetadata, EvidenceFile
from app.modules.evidences.domain.exceptions import SessionClosedForEvidenceError
from app.modules.evidences.domain.repositories import EvidenceRepository, EvidenceStorage


@dataclass(frozen=True)
class UploadAudioEvidenceCommand:
    session: Any
    current_user: Any
    file: EvidenceFile
    metadata: AudioEvidenceMetadata


class UploadAudioEvidenceUseCase:
    def __init__(self, repository: EvidenceRepository, storage: EvidenceStorage) -> None:
        self.repository = repository
        self.storage = storage

    def execute(self, command: UploadAudioEvidenceCommand):
        if command.session.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
            raise SessionClosedForEvidenceError()

        audio_url = self.storage.upload_bytes(
            content=command.file.content,
            folder="audio-samples",
            filename=command.file.filename,
            content_type=command.file.content_type,
        )
        self.repository.clear_audio_analysis_and_result(command.session)
        sample = self.repository.create_or_update_audio_sample(
            session=command.session,
            audio_url=audio_url,
            locale=command.metadata.locale,
            duration_seconds=command.metadata.duration_seconds,
        )
        self.repository.add(sample)
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="upload_audio_sample",
            entity_type="audio_sample",
            entity_id=sample.id,
        )
        return sample

