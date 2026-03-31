from __future__ import annotations

from app.domain.enums import RiskFlag


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
        RiskFlag.LOW: "Indicadores dentro de un rango esperado para seguimiento pedagógico. Este resultado no equivale a un diagnóstico clínico.",
        RiskFlag.MEDIUM: "Se observan indicadores que sugieren seguimiento docente cercano y nueva revisión. Este resultado no equivale a un diagnóstico clínico.",
        RiskFlag.HIGH_REVIEW: "Se recomienda revisión pedagógica prioritaria y posible derivación según protocolo institucional. Este resultado no equivale a un diagnóstico clínico.",
    }
    return observations[risk_flag]
