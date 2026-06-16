from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.ocr_analysis import OCRAnalysis
from app.models.pronunciation_analysis import PronunciationAnalysis
from app.models.session_result import SessionResult
from app.assessment.modules.evidences.infrastructure.models import AudioSample, WritingSample
from app.services.audit import create_audit_log


class SQLAlchemyEvidenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def clear_writing_analysis_and_result(self, session) -> None:
        if session.writing_sample:
            self.db.execute(delete(OCRAnalysis).where(OCRAnalysis.writing_sample_id == session.writing_sample.id))
        self.db.execute(delete(SessionResult).where(SessionResult.session_id == session.id))
        self.db.flush()

    def clear_audio_analysis_and_result(self, session) -> None:
        if session.audio_sample:
            self.db.execute(delete(PronunciationAnalysis).where(PronunciationAnalysis.audio_sample_id == session.audio_sample.id))
        self.db.execute(delete(SessionResult).where(SessionResult.session_id == session.id))
        self.db.flush()

    def create_or_update_writing_sample(
        self,
        *,
        session,
        image_url: str,
        source_type: str,
        stroke_count: int | None,
        correction_count: int | None,
        duration_seconds: int | None,
    ) -> WritingSample:
        sample = session.writing_sample or WritingSample(session_id=session.id, image_url=image_url, source_type=source_type)
        sample.image_url = image_url
        sample.source_type = source_type
        sample.stroke_count = stroke_count
        sample.correction_count = correction_count
        sample.duration_seconds = duration_seconds
        sample.captured_at = datetime.now(UTC)
        return sample

    def create_or_update_audio_sample(
        self,
        *,
        session,
        audio_url: str,
        locale: str,
        duration_seconds: int | None,
    ) -> AudioSample:
        sample = session.audio_sample or AudioSample(session_id=session.id, audio_url=audio_url, locale=locale)
        sample.audio_url = audio_url
        sample.locale = locale
        sample.duration_seconds = duration_seconds
        sample.captured_at = datetime.now(UTC)
        return sample

    def add(self, entity) -> None:
        self.db.add(entity)

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        create_audit_log(self.db, user=user, action=action, entity_type=entity_type, entity_id=entity_id)

    def flush(self) -> None:
        self.db.flush()
