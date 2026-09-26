from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from app.assessment.application.exceptions_speech_to_text import (
    CrisperWhisperDeviceError,
    CrisperWhisperInferenceError,
    CrisperWhisperModelLoadError,
    CrisperWhisperModelUnavailableError,
    CrisperWhisperOutOfMemoryError,
)
from app.assessment.application.ports.speech_to_text import (
    SpeechToTextPort,
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionWord,
)


CRISPER_MODEL_IDS = {
    "small": "nyralabs/CrisperWhisper2.0_small",
    "medium": "nyralabs/CrisperWhisper2.0_medium",
    "large": "nyralabs/CrisperWhisper2.0_large",
    "turbo": "nyralabs/CrisperWhisper2.0_turbo",
}


@dataclass(frozen=True)
class CrisperWhisperConfig:
    provider: str = "crisper_whisper"
    model_size: str = "medium"
    mode: str = "verbatim"
    device: str = "cpu"
    compute_type: str = "float32"
    language: str = "es"
    word_timestamps: bool = True
    download_root: str | None = None
    low_confidence_threshold: float = -1.0

    @property
    def model_id(self) -> str:
        return CRISPER_MODEL_IDS.get(self.model_size, self.model_size)

    @classmethod
    def from_settings(cls, settings: Any) -> "CrisperWhisperConfig":
        config = cls(
            provider=settings.assessment_stt_provider,
            model_size=settings.crisper_model_size,
            mode=settings.crisper_mode,
            device=settings.crisper_device,
            compute_type=settings.crisper_compute_type,
            language=settings.crisper_language,
            word_timestamps=settings.crisper_word_timestamps,
            download_root=settings.crisper_model_download_root,
            low_confidence_threshold=settings.whisper_low_confidence_threshold,
        )
        if config.provider != "crisper_whisper":
            raise ValueError(f"Unsupported assessment STT provider: {config.provider}")
        if config.language != "es":
            raise ValueError("Assessment CrisperWhisper language must be 'es'")
        if config.mode not in {"verbatim", "intended"}:
            raise ValueError("CRISPER_MODE must be 'verbatim' or 'intended'")
        if config.model_size not in CRISPER_MODEL_IDS and not config.model_size.startswith(
            "nyralabs/CrisperWhisper2.0_"
        ):
            raise ValueError(
                "CRISPER_MODEL_SIZE must be one of small, medium, large, turbo "
                "or a nyralabs/CrisperWhisper2.0_* model id"
            )
        return config


class CrisperWhisperModelProvider:
    """Lazy process-local model cache; each server worker owns its own cache."""

    _models: dict[tuple[str, str, str, str | None], Any] = {}
    _lock = threading.Lock()

    def __init__(self, model_factory: Callable[..., Any] | None = None) -> None:
        self._model_factory = model_factory

    def get_model(self, config: CrisperWhisperConfig) -> tuple[Any, int | None]:
        key = (
            config.model_id,
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
                    from crisperwhisper import CrisperWhisperModel
                except ImportError as exc:
                    raise CrisperWhisperModelUnavailableError() from exc
                factory = CrisperWhisperModel
            started = time.perf_counter()
            try:
                kwargs = {
                    "backend": "transformers",
                    "device": config.device,
                    "compute_type": config.compute_type,
                }
                if config.download_root:
                    kwargs["download_root"] = config.download_root
                model = factory(config.model_id, **kwargs)
            except MemoryError as exc:
                raise CrisperWhisperOutOfMemoryError() from exc
            except Exception as exc:
                message = str(exc).lower()
                if "cuda" in message or "compute type" in message:
                    raise CrisperWhisperDeviceError() from exc
                if "memory" in message or "allocate" in message:
                    raise CrisperWhisperOutOfMemoryError() from exc
                raise CrisperWhisperModelLoadError() from exc
            load_time_ms = round((time.perf_counter() - started) * 1000)
            self._models[key] = model
            return model, load_time_ms

    @classmethod
    def clear_cache(cls) -> None:
        cls._models.clear()


class CrisperWhisperSpeechToTextAdapter(SpeechToTextPort):
    def __init__(
        self,
        config: CrisperWhisperConfig,
        model_provider: CrisperWhisperModelProvider | None = None,
    ) -> None:
        self.config = config
        self._model_provider = model_provider or CrisperWhisperModelProvider()

    async def transcribe(
        self,
        audio_path: str,
        language: str = "es",
    ) -> TranscriptionResult:
        if language != "es" or self.config.language != "es":
            raise CrisperWhisperInferenceError("Only Spanish transcription is supported")
        return await asyncio.to_thread(self._transcribe_sync, audio_path)

    def _transcribe_sync(self, audio_path: str) -> TranscriptionResult:
        model, load_time_ms = self._model_provider.get_model(self.config)
        started = time.perf_counter()
        try:
            result = model.transcribe(
                audio_path,
                language="es",
                mode=self.config.mode,
                word_timestamps=self.config.word_timestamps,
            )
        except MemoryError as exc:
            raise CrisperWhisperOutOfMemoryError() from exc
        except Exception as exc:
            message = str(exc).lower()
            if "cuda" in message:
                raise CrisperWhisperDeviceError() from exc
            if "memory" in message or "allocate" in message:
                raise CrisperWhisperOutOfMemoryError() from exc
            raise CrisperWhisperInferenceError() from exc
        processing_time_ms = round((time.perf_counter() - started) * 1000)

        text = str(getattr(result, "text", "") or "").strip()
        duration = _optional_float(getattr(result, "duration", None))
        words = self._convert_words(getattr(result, "words", None) or [])
        segment = self._build_segment(text, words, duration)
        warnings: list[str] = []
        if not text:
            warnings.append("EMPTY_TRANSCRIPTION")
        real_time_factor = (
            round((processing_time_ms / 1000) / duration, 4)
            if duration and duration > 0
            else None
        )
        return TranscriptionResult(
            text=text,
            language=str(getattr(result, "language", "es") or "es"),
            language_probability=None,
            duration_seconds=duration,
            segments=[segment],
            provider="crisper_whisper",
            model=self.config.model_id,
            warnings=warnings,
            confidence_heuristic=None,
            processing_time_ms=processing_time_ms,
            model_load_time_ms=load_time_ms,
            real_time_factor=real_time_factor,
        )

    @staticmethod
    def _convert_words(words: list[Any]) -> list[TranscriptionWord]:
        return [
            TranscriptionWord(
                text=str(getattr(word, "word", getattr(word, "text", ""))).strip(),
                start_seconds=_optional_float(getattr(word, "start", None)),
                end_seconds=_optional_float(getattr(word, "end", None)),
                probability=None,
            )
            for word in words
        ]

    @staticmethod
    def _build_segment(
        text: str,
        words: list[TranscriptionWord],
        duration: float | None,
    ) -> TranscriptionSegment:
        starts = [word.start_seconds for word in words if word.start_seconds is not None]
        ends = [word.end_seconds for word in words if word.end_seconds is not None]
        start_seconds = min(starts) if starts else 0.0
        end_seconds = max(ends) if ends else (duration or 0.0)
        return TranscriptionSegment(
            text=text,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            avg_logprob=None,
            no_speech_prob=None,
            words=words,
        )


def _optional_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
