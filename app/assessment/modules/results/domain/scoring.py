from __future__ import annotations

from app.domain.enums import RiskFlag
from app.assessment.modules.results.domain.entities import ConsolidatedScores


def build_overall_score(writing_score: float | None, reading_score: float | None) -> float | None:
    values = [value for value in [writing_score, reading_score] if value is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def build_risk_flag(overall_score: float | None, writing_score: float | None, reading_score: float | None) -> RiskFlag:
    relevant = [value for value in [overall_score, writing_score, reading_score] if value is not None]
    if not relevant:
        return RiskFlag.MEDIUM
    if min(relevant) < 45 or (overall_score is not None and overall_score < 50):
        return RiskFlag.HIGH_REVIEW
    if min(relevant) < 70 or (overall_score is not None and overall_score < 75):
        return RiskFlag.MEDIUM
    return RiskFlag.LOW


def build_observation(risk_flag: RiskFlag) -> str:
    observations = {
        RiskFlag.LOW: "Indicadores dentro de un rango esperado para seguimiento pedagogico. Este resultado no equivale a un diagnostico clinico.",
        RiskFlag.MEDIUM: "Se observan indicadores que sugieren seguimiento docente cercano y nueva revision. Este resultado no equivale a un diagnostico clinico.",
        RiskFlag.HIGH_REVIEW: "Se recomienda revision pedagogica prioritaria y posible derivacion segun protocolo institucional. Este resultado no equivale a un diagnostico clinico.",
    }
    return observations[risk_flag]


def consolidate_scores(writing_score: float | None, reading_score: float | None) -> ConsolidatedScores:
    overall_score = build_overall_score(writing_score, reading_score)
    risk_flag = build_risk_flag(overall_score, writing_score, reading_score)
    return ConsolidatedScores(
        writing_score=writing_score,
        reading_score=reading_score,
        overall_score=overall_score,
        risk_flag=risk_flag,
        observation=build_observation(risk_flag),
    )

