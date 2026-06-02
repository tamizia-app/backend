from __future__ import annotations

from app.modules.ai_processing.domain.entities import WritingMetrics
from app.modules.ai_processing.domain.text_metrics import calculate_writing_metrics


class CalculateWritingMetricsUseCase:
    def execute(self, *, reference_text: str, observed_text: str) -> WritingMetrics:
        return calculate_writing_metrics(reference_text, observed_text)

