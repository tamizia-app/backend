from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceFile:
    content: bytes
    filename: str
    content_type: str


@dataclass(frozen=True)
class WritingEvidenceMetadata:
    source_type: str
    stroke_count: int | None
    correction_count: int | None
    duration_seconds: int | None


@dataclass(frozen=True)
class AudioEvidenceMetadata:
    locale: str
    duration_seconds: int | None

