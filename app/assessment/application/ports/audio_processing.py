from __future__ import annotations

from typing import Any, Protocol


class PreparedAudioPort(Protocol):
    path: str
    original: Any
    azure_input: Any
    normalized: bool
    warnings: list[str]

    def cleanup(self) -> None: ...


class AudioPreparationPort(Protocol):
    def prepare(
        self,
        audio_content: bytes,
        audio_format: str | None = None,
    ) -> PreparedAudioPort: ...
