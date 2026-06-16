from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import Settings


@dataclass
class OCRServiceResult:
    extracted_text: str
    confidence_avg: float | None
    raw_response: dict


class OCRService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze_image(self, image_bytes: bytes) -> OCRServiceResult:
        if not self.settings.azure_vision_endpoint or not self.settings.azure_vision_key:
            return OCRServiceResult(
                extracted_text="",
                confidence_avg=None,
                raw_response={"provider": "mock", "message": "Azure Vision is not configured."},
            )

        endpoint = self.settings.azure_vision_endpoint.rstrip("/")
        url = f"{endpoint}/computervision/imageanalysis:analyze"
        params = {"api-version": "2023-02-01-preview", "features": "read", "language": "es"}
        headers = {
            "Ocp-Apim-Subscription-Key": self.settings.azure_vision_key,
            "Content-Type": "application/octet-stream",
        }

        response = httpx.post(url, params=params, headers=headers, content=image_bytes, timeout=60.0)
        response.raise_for_status()
        payload = response.json()

        extracted_lines: list[str] = []
        confidences: list[float] = []
        for block in payload.get("readResult", {}).get("blocks", []):
            for line in block.get("lines", []):
                text = line.get("text")
                if text:
                    extracted_lines.append(text)
                for word in line.get("words", []):
                    confidence = word.get("confidence")
                    if confidence is not None:
                        confidences.append(float(confidence))

        return OCRServiceResult(
            extracted_text=" ".join(extracted_lines).strip(),
            confidence_avg=round(sum(confidences) / len(confidences), 4) if confidences else None,
            raw_response=payload,
        )

