from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.results.domain.entities import ConsolidatedScores
from app.modules.results.infrastructure.models import SessionResult
from app.services.audit import create_audit_log


class SQLAlchemyResultRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_or_update_session_result(self, *, session, scores: ConsolidatedScores) -> SessionResult:
        result = session.result or SessionResult(
            session_id=session.id,
            observation=scores.observation,
            risk_flag=scores.risk_flag,
        )
        result.writing_score = scores.writing_score
        result.reading_score = scores.reading_score
        result.overall_score = scores.overall_score
        result.risk_flag = scores.risk_flag
        result.observation = scores.observation
        result.generated_at = datetime.now(UTC)
        return result

    def get_by_session(self, session_id: UUID) -> SessionResult | None:
        return self.db.scalar(select(SessionResult).where(SessionResult.session_id == session_id))

    def list_by_student(self, student_id: UUID) -> list[SessionResult]:
        query = (
            select(SessionResult)
            .join(SessionResult.session)
            .where(SessionResult.session.has(student_id=student_id))
            .order_by(SessionResult.generated_at.desc())
        )
        return list(self.db.scalars(query))

    def add(self, result: SessionResult) -> None:
        self.db.add(result)

    def record_audit(self, *, user, action: str, entity_type: str, entity_id) -> None:
        create_audit_log(self.db, user=user, action=action, entity_type=entity_type, entity_id=entity_id)

    def flush(self) -> None:
        self.db.flush()
