from __future__ import annotations

from app.assessment.modules.ai_processing.domain.entities import TextComparison
from app.assessment.modules.ai_processing.domain.text_metrics import compare_expected_text as compare_text


class CompareExpectedTextUseCase:
    def execute(self, *, reference_text: str, observed_text: str) -> TextComparison:
        return compare_text(reference_text, observed_text)

