from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.enums import SessionStatus
from app.modules.ai_processing.domain.exceptions import SessionClosedForAnalysisError, WritingSampleRequiredError
from app.modules.ai_processing.domain.repositories import AIProcessingRepository, BinarySourceLoader, OCRProcessor
from app.modules.ai_processing.domain.text_metrics import calculate_writing_metrics


@dataclass(frozen=True)
class ProcessWritingOCRCommand:
    session: Any
    current_user: Any


class ProcessWritingOCRUseCase:
    def __init__(
        self,
        *,
        repository: AIProcessingRepository,
        binary_loader: BinarySourceLoader,
        ocr_processor: OCRProcessor,
    ) -> None:
        self.repository = repository
        self.binary_loader = binary_loader
        self.ocr_processor = ocr_processor

    def execute(self, command: ProcessWritingOCRCommand):
        if command.session.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
            raise SessionClosedForAnalysisError()
        if not command.session.writing_sample:
            raise WritingSampleRequiredError()

        image_bytes = self.binary_loader.load(command.session.writing_sample.image_url)
        ocr_result = self.ocr_processor.analyze_image(image_bytes)
        metrics = calculate_writing_metrics(command.session.exercise.reference_text, ocr_result.extracted_text)
        comparison = metrics.comparison

        analysis = self.repository.create_or_update_ocr_analysis(
            writing_sample=command.session.writing_sample,
            extracted_text=ocr_result.extracted_text,
            confidence_avg=ocr_result.confidence_avg,
            cer_score=comparison.cer_score,
            wer_score=comparison.wer_score,
            omissions=comparison.omissions,
            substitutions=comparison.substitutions,
            raw_response=ocr_result.raw_response,
        )
        self.repository.add(analysis)
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="analyze_writing",
            entity_type="ocr_analysis",
            entity_id=analysis.id,
        )
        return analysis, metrics.writing_score

