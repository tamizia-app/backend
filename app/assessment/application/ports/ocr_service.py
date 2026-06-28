from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class OcrResult:
    full_text: str = ""
    confidence_avg: float | None = None
    raw_response: dict = field(default_factory=dict)
    error_message: str | None = None
    error_code: str | None = None


class OcrService(Protocol):
    def extract_text(self, image_data: bytes) -> OcrResult: ...
