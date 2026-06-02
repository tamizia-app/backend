from __future__ import annotations

from typing import Any, Protocol


class EvidenceRepository(Protocol):
    def clear_writing_analysis_and_result(self, session: Any) -> None:
        ...

    def clear_audio_analysis_and_result(self, session: Any) -> None:
        ...

    def create_or_update_writing_sample(
        self,
        *,
        session: Any,
        image_url: str,
        source_type: str,
        stroke_count: int | None,
        correction_count: int | None,
        duration_seconds: int | None,
    ) -> Any:
        ...

    def create_or_update_audio_sample(
        self,
        *,
        session: Any,
        audio_url: str,
        locale: str,
        duration_seconds: int | None,
    ) -> Any:
        ...

    def add(self, entity: Any) -> None:
        ...

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        ...

    def flush(self) -> None:
        ...


class EvidenceStorage(Protocol):
    def upload_bytes(self, *, content: bytes, folder: str, filename: str, content_type: str) -> str:
        ...

