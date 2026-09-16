from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.ports.repositories import ExerciseScoreRepository
from app.assessment.domain.enums import ExerciseType
from app.assessment.domain.metrics import ExerciseScore
from app.assessment.domain.technical_quality import TechnicalQuality


def persist_exercise_score(
    repository: ExerciseScoreRepository,
    *,
    exercise_attempt_id: UUID,
    exercise_type: ExerciseType,
    score: float | None,
    quality: TechnicalQuality,
    scoring_components: dict,
) -> ExerciseScore:
    now = datetime.now(timezone.utc)
    existing = repository.find_by_exercise_attempt_id(exercise_attempt_id)
    original_score = existing.original_score if existing and existing.original_score is not None else score
    original_components = (
        existing.original_scoring_components
        if existing and existing.original_scoring_components
        else scoring_components
    )
    return repository.upsert(
        ExerciseScore(
            id=existing.id if existing else UUID(int=0),
            exercise_attempt_id=exercise_attempt_id,
            exercise_type=exercise_type,
            score=score,
            score_eligible=quality.score_eligible,
            technical_status=quality.technical_status,
            manual_review_required=quality.manual_review_required,
            quality_reasons=quality.quality_reasons,
            scoring_components=scoring_components,
            created_at=existing.created_at if existing else now,
            updated_at=now,
            original_score=original_score,
            current_score=score,
            original_scoring_components=original_components,
            current_scoring_components=scoring_components,
            manual_adjustment_applied=False,
            teacher_observation=None,
            adjusted_by_teacher_id=None,
            adjusted_at=None,
        )
    )
