from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from app.assessment.application.exceptions_speech_to_text import (
    WhisperDeviceError,
    WhisperInferenceError,
    WhisperModelLoadError,
    WhisperModelUnavailableError,
    WhisperOutOfMemoryError,
)
from app.assessment.application.ports.speech_to_text import (
    SpeechToTextPort,
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionWord,
)


@dataclass(frozen=True)
class WhisperConfig:
    provider: str = "faster_whisper"
    model_size: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "es"
    beam_size: int = 5
    word_timestamps: bool = True
    vad_filter: bool = False
    download_root: str | None = None
    low_confidence_threshold: float = -1.0

    @classmethod
    def from_settings(cls, settings: Any) -> "WhisperConfig":
        config = cls(
            provider=settings.assessment_stt_provider,
            model_size=settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            language=settings.whisper_language,
            beam_size=settings.whisper_beam_size,
            word_timestamps=settings.whisper_word_timestamps,
            vad_filter=settings.whisper_vad_filter,
            download_root=settings.whisper_model_download_root,
            low_confidence_threshold=settings.whisper_low_confidence_threshold,
        )
        if config.provider != "faster_whisper":
            raise ValueError(f"Unsupported assessment STT provider: {config.provider}")
        if config.language != "es":
            raise ValueError("Assessment Whisper language must be 'es'")
        if config.beam_size < 1:
            raise ValueError("WHISPER_BEAM_SIZE must be at least 1")
        return config


class FasterWhisperModelProvider:
    """Lazy process-local model cache; each server worker owns its own cache."""

    _models: dict[tuple[str, str, str, str | None], Any] = {}
    _load_times_ms: dict[tuple[str, str, str, str | None], int] = {}
    _lock = threading.Lock()

    def __init__(self, model_factory: Callable[..., Any] | None = None) -> None:
        self._model_factory = model_factory

    def get_model(self, config: WhisperConfig) -> tuple[Any, int | None]:
        key = (
            config.model_size,
            config.device,
            config.compute_type,
            config.download_root,
        )
        existing = self._models.get(key)
        if existing is not None:
            return existing, None
        with self._lock:
            existing = self._models.get(key)
            if existing is not None:
                return existing, None
            factory = self._model_factory
            if factory is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as exc:
                    raise WhisperModelUnavailableError() from exc
                factory = WhisperModel
            started = time.perf_counter()
            try:
                model = factory(
                    config.model_size,
                    device=config.device,
                    compute_type=config.compute_type,
                    download_root=config.download_root,
                )
            except MemoryError as exc:
                raise WhisperOutOfMemoryError() from exc
            except Exception as exc:
                message = str(exc).lower()
                if "cuda" in message or "compute type" in message:
                    raise WhisperDeviceError() from exc
                if "memory" in message or "allocate" in message:
                    raise WhisperOutOfMemoryError() from exc
                raise WhisperModelLoadError() from exc
            load_time_ms = round((time.perf_counter() - started) * 1000)
            self._models[key] = model
            self._load_times_ms[key] = load_time_ms
            return model, load_time_ms

    @classmethod
    def clear_cache(cls) -> None:
        cls._models.clear()
        cls._load_times_ms.clear()


class FasterWhisperSpeechToTextAdapter(SpeechToTextPort):
    def __init__(
        self,
        config: WhisperConfig,
        model_provider: FasterWhisperModelProvider | None = None,
    ) -> None:
        self.config = config
        self._model_provider = model_provider or FasterWhisperModelProvider()

    async def transcribe(
        self,
        audio_path: str,
        language: str = "es",
    ) -> TranscriptionResult:
        if language != "es" or self.config.language != "es":
            raise WhisperInferenceError("Only Spanish transcription is supported")
        return await asyncio.to_thread(self._transcribe_sync, audio_path)

    def _transcribe_sync(self, audio_path: str) -> TranscriptionResult:
        model, load_time_ms = self._model_provider.get_model(self.config)
        started = time.perf_counter()
        try:
            segment_iterator, info = model.transcribe(
                audio_path,
                language="es",
                beam_size=self.config.beam_size,
                word_timestamps=self.config.word_timestamps,
                vad_filter=self.config.vad_filter,
                condition_on_previous_text=False,
            )
            raw_segments = list(segment_iterator)
        except MemoryError as exc:
            raise WhisperOutOfMemoryError() from exc
        except Exception as exc:
            message = str(exc).lower()
            if "cuda" in message:
                raise WhisperDeviceError() from exc
            if "memory" in message or "allocate" in message:
                raise WhisperOutOfMemoryError() from exc
            raise WhisperInferenceError() from exc
        processing_time_ms = round((time.perf_counter() - started) * 1000)

        segments = [self._convert_segment(segment) for segment in raw_segments]
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        duration = _optional_float(getattr(info, "duration", None))
        warnings: list[str] = []
        if not text:
            warnings.append("EMPTY_TRANSCRIPTION")
        if any(
            segment.no_speech_prob is not None and segment.no_speech_prob >= 0.6
            for segment in segments
        ):
            warnings.append("HIGH_NO_SPEECH_PROBABILITY")
        real_time_factor = (
            round((processing_time_ms / 1000) / duration, 4)
            if duration and duration > 0
            else None
        )
        return TranscriptionResult(
            text=text,
            language=str(getattr(info, "language", "es") or "es"),
            language_probability=_optional_float(
                getattr(info, "language_probability", None)
            ),
            duration_seconds=duration,
            segments=segments,
            provider="faster_whisper",
            model=self.config.model_size,
            warnings=warnings,
            confidence_heuristic=None,
            processing_time_ms=processing_time_ms,
            model_load_time_ms=load_time_ms,
            real_time_factor=real_time_factor,
        )

    @staticmethod
    def _convert_segment(segment: Any) -> TranscriptionSegment:
        words = [
            TranscriptionWord(
                text=str(getattr(word, "word", "")).strip(),
                start_seconds=_optional_float(getattr(word, "start", None)),
                end_seconds=_optional_float(getattr(word, "end", None)),
                probability=_optional_float(getattr(word, "probability", None)),
            )
            for word in (getattr(segment, "words", None) or [])
        ]
        return TranscriptionSegment(
            text=str(getattr(segment, "text", "")).strip(),
            start_seconds=float(getattr(segment, "start", 0.0)),
            end_seconds=float(getattr(segment, "end", 0.0)),
            avg_logprob=_optional_float(getattr(segment, "avg_logprob", None)),
            no_speech_prob=_optional_float(getattr(segment, "no_speech_prob", None)),
            words=words,
        )


def _optional_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
