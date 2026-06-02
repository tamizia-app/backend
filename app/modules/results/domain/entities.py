from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import RiskFlag


@dataclass(frozen=True)
class ConsolidatedScores:
    writing_score: float | None
    reading_score: float | None
    overall_score: float | None
    risk_flag: RiskFlag
    observation: str

