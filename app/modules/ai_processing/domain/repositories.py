from __future__ import annotations

from typing import Any, Protocol


class AIProcessingRepository(Protocol):
    def create_or_update_ocr_analysis(
        self,
        *,
        writing_sample: Any,
        extracted_text: str,
        confidence_avg: float | None,
        cer_score: float,
        wer_score: float,
        omissions: int,
        substitutions: int,
        raw_response: dict,
    ) -> Any:
        ...

    def create_or_update_pronunciation_analysis(
        self,
        *,
        audio_sample: Any,
        accuracy_score: float | None,
        fluency_score: float | None,
        completeness_score: float | None,
        pronunciation_score: float | None,
        recognized_text: str | None,
        raw_response: dict,
    ) -> Any:
        ...

    def add(self, entity: Any) -> None:
        ...

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        ...

    def flush(self) -> None:
        ...


class BinarySourceLoader(Protocol):
    def load(self, location: str) -> bytes:
        ...


class OCRProcessor(Protocol):
    def analyze_image(self, image_bytes: bytes) -> Any:
        ...


class PronunciationProcessor(Protocol):
    def analyze_audio(self, *, audio_bytes: bytes, reference_text: str, locale: str) -> Any:
        ...
