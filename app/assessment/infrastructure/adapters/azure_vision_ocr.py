from __future__ import annotations

import json
import logging

from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from app.assessment.application.ports.ocr_service import OcrResult
from app.core.config import Settings

logger = logging.getLogger(__name__)


class AzureVisionOcrAdapter:
    def __init__(self, settings: Settings) -> None:
        self._client = ImageAnalysisClient(
            endpoint=settings.azure_vision_endpoint,
            credential=AzureKeyCredential(settings.azure_vision_key),
        )

    def extract_text(self, image_data: bytes) -> OcrResult:
        try:
            result = self._client.analyze(
                image_data=image_data,
                visual_features=[VisualFeatures.READ],
            )
        except HttpResponseError as exc:
            logger.error("Azure Vision OCR HTTP error: %s", exc)
            return OcrResult(
                error_code="http_error",
                error_message=f"Azure Vision OCR failed: {exc.message}",
            )
        except Exception as exc:
            logger.exception("Azure Vision OCR failed")
            return OcrResult(
                error_code="ocr_error",
                error_message=f"Azure Vision OCR failed: {exc}",
            )

        if result.read is None:
            logger.warning("Azure Vision returned no READ result")
            return OcrResult()

        lines = []
        confidences = []
        raw_lines = []

        for block in result.read.blocks:
            for line in block.lines:
                lines.append(line.text)
                raw_line = {"text": line.text, "words": []}
                for word in line.words:
                    raw_line["words"].append(
                        {
                            "text": word.text,
                            "confidence": word.confidence,
                            "bounding_polygon": [
                                {"x": p.x, "y": p.y} for p in word.bounding_polygon
                            ],
                        }
                    )
                    if word.confidence is not None:
                        confidences.append(word.confidence)
                raw_lines.append(raw_line)

        full_text = "\n".join(lines)
        confidence_avg = round(sum(confidences) / len(confidences), 4) if confidences else None

        raw_response = {
            "blocks": [
                {
                    "lines": raw_lines,
                }
            ],
        }

        return OcrResult(
            full_text=full_text,
            confidence_avg=confidence_avg,
            raw_response=raw_response,
        )
