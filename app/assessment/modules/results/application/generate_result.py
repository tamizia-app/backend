from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.assessment.modules.ai_processing.domain.text_metrics import build_reading_score, build_writing_score
from app.assessment.modules.results.domain.exceptions import AnalysisRequiredError
from app.assessment.modules.results.domain.repositories import ResultRepository
from app.assessment.modules.results.domain.scoring import consolidate_scores


@dataclass(frozen=True)
class GenerateResultCommand:
    session: Any
    current_user: Any


class GenerateResultUseCase:
    def __init__(self, repository: ResultRepository) -> None:
        self.repository = repository

    def execute(self, command: GenerateResultCommand):
        writing_score = None
        if command.session.writing_sample and command.session.writing_sample.analysis:
            writing_score = build_writing_score(
                cer_score=command.session.writing_sample.analysis.cer_score,
                wer_score=command.session.writing_sample.analysis.wer_score,
                omissions=command.session.writing_sample.analysis.omissions,
                substitutions=command.session.writing_sample.analysis.substitutions,
            )

        reading_score = None
        if command.session.audio_sample and command.session.audio_sample.analysis:
            reading_score = build_reading_score(
                accuracy_score=command.session.audio_sample.analysis.accuracy_score,
                fluency_score=command.session.audio_sample.analysis.fluency_score,
                completeness_score=command.session.audio_sample.analysis.completeness_score,
                pronunciation_score=command.session.audio_sample.analysis.pronunciation_score,
            )

        if writing_score is None and reading_score is None:
            raise AnalysisRequiredError()

        scores = consolidate_scores(writing_score, reading_score)
        result = self.repository.create_or_update_session_result(session=command.session, scores=scores)
        self.repository.add(result)
        self.repository.flush()
        self.repository.record_audit(
            user=command.current_user,
            action="generate_result",
            entity_type="session_result",
            entity_id=result.id,
        )
        return result

