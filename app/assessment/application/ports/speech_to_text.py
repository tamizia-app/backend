from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class TranscriptionWord:
    text: str
    start_seconds: float | None
    end_seconds: float | None
    probability: float | None


@dataclass(frozen=True)
class TranscriptionSegment:
    text: str
    start_seconds: float
    end_seconds: float
    avg_logprob: float | None
    no_speech_prob: float | None
    words: list[TranscriptionWord] = field(default_factory=list)


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    language_probability: float | None
    duration_seconds: float | None
    segments: list[TranscriptionSegment]
    provider: str
    model: str
    warnings: list[str] = field(default_factory=list)
    confidence_heuristic: float | None = None
    processing_time_ms: int | None = None
    model_load_time_ms: int | None = None
    real_time_factor: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class SpeechToTextPort(Protocol):
    async def transcribe(
        self,
        audio_path: str,
        language: str = "es",
    ) -> TranscriptionResult: ...
