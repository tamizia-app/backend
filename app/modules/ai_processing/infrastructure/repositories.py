from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.ai_processing.infrastructure.models import OCRAnalysis, PronunciationAnalysis
from app.services.audit import create_audit_log


class SQLAlchemyAIProcessingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_or_update_ocr_analysis(
        self,
        *,
        writing_sample,
        extracted_text: str,
        confidence_avg: float | None,
        cer_score: float,
        wer_score: float,
        omissions: int,
        substitutions: int,
        raw_response: dict,
    ) -> OCRAnalysis:
        analysis = writing_sample.analysis or OCRAnalysis(writing_sample_id=writing_sample.id)
        analysis.extracted_text = extracted_text
        analysis.confidence_avg = confidence_avg
        analysis.cer_score = round(cer_score, 4)
        analysis.wer_score = round(wer_score, 4)
        analysis.omissions = omissions
        analysis.substitutions = substitutions
        analysis.raw_response = raw_response
        analysis.analyzed_at = datetime.now(UTC)
        return analysis

    def create_or_update_pronunciation_analysis(
        self,
        *,
        audio_sample,
        accuracy_score: float | None,
        fluency_score: float | None,
        completeness_score: float | None,
        pronunciation_score: float | None,
        recognized_text: str | None,
        raw_response: dict,
    ) -> PronunciationAnalysis:
        analysis = audio_sample.analysis or PronunciationAnalysis(audio_sample_id=audio_sample.id)
        analysis.accuracy_score = accuracy_score
        analysis.fluency_score = fluency_score
        analysis.completeness_score = completeness_score
        analysis.pronunciation_score = pronunciation_score
        analysis.recognized_text = recognized_text
        analysis.raw_response = raw_response
        analysis.analyzed_at = datetime.now(UTC)
        return analysis

    def add(self, entity) -> None:
        self.db.add(entity)

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        create_audit_log(self.db, user=user, action=action, entity_type=entity_type, entity_id=entity_id)

    def flush(self) -> None:
        self.db.flush()
