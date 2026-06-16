from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.enums import SessionStatus
from app.assessment.modules.ai_processing.domain.exceptions import AudioSampleRequiredError, SessionClosedForAnalysisError
from app.assessment.modules.ai_processing.domain.repositories import AIProcessingRepository, BinarySourceLoader, PronunciationProcessor
from app.assessment.modules.ai_processing.domain.text_metrics import calculate_reading_metrics


@dataclass(frozen=True)
class ProcessReadingPronunciationCommand:
    session: Any
    current_user: Any


class ProcessReadingPronunciationUseCase:
    def __init__(
        self,
        *,
        repository: AIProcessingRepository,
        binary_loader: BinarySourceLoader,
        pronunciation_processor: PronunciationProcessor,
    ) -> None:
        self.repository = repository
        self.binary_loader = binary_loader
        self.pronunciation_processor = pronunciation_processor

    def execute(self, command: ProcessReadingPronunciationCommand):
        if command.session.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
            raise SessionClosedForAnalysisError()
        if not command.session.audio_sample:
            raise AudioSampleRequiredError()

        audio_bytes = self.binary_loader.load(command.session.audio_sample.audio_url)
        pronunciation_result = self.pronunciation_processor.analyze_audio(
            audio_bytes=audio_bytes,
            reference_text=command.session.exercise.reference_text,
            locale=command.session.audio_sample.locale,
        )
        metrics = calculate_reading_metrics(
            accuracy_score=pronunciation_result.accuracy_score,
            fluency_score=pronunciation_result.fluency_score,
            completeness_score=pronunciation_result.completeness_score,
            pronunciation_score=pronunciation_result.pronunciation_score,
        )

        analysis = self.repository.create_or_update_pronunciation_analysis(
            audio_sample=command.session.audio_sample,
            accuracy_score=pronunciation_result.accuracy_score,
            fluency_score=pronunciation_result.fluency_score,
            completeness_score=pronunciation_result.completeness_score,
            pronunciation_score=pronunciation_result.pronunciation_score,
            recognized_text=pronunciation_result.recognized_text,
            raw_response=pronunciation_result.raw_response,
        )
        self.repository.add(analysis)
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="analyze_reading",
            entity_type="pronunciation_analysis",
            entity_id=analysis.id,
        )
        return analysis, metrics.reading_score
