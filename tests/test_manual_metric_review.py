from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.assessment.application.exceptions import InvalidExerciseTypeError
from app.assessment.application.use_cases.manual_review_exercise_attempt import (
    ManualReviewExerciseAttemptCommand,
    ManualReviewExerciseAttemptUseCase,
)
from app.assessment.domain.assessment import Assessment
from app.assessment.domain.attempt import AssessmentAttempt, ExerciseAttempt
from app.assessment.domain.enums import AssessmentStatus, AttemptStatus, ExerciseAttemptStatus, ExerciseType, TechnicalStatus
from app.assessment.domain.exercise import AssessmentExercise
from app.assessment.domain.metrics import ExerciseScore, SpeakingMetrics
from app.assessment.domain.response import SpeakingResponse
from app.assessment.domain.template import AssessmentTemplateExercise


def test_manual_review_speaking_updates_current_only_and_recalculates_score():
    fixture = _fixture(TechnicalStatus.VALID, score_eligible=True)
    result = fixture.use_case.execute(
        ManualReviewExerciseAttemptCommand(
            exercise_attempt_id=fixture.exercise_attempt_id,
            teacher_id=fixture.teacher_id,
            metrics={"accuracy_score": 90, "fluency_score": 80},
            teacher_observation="Ajuste docente.",
        )
    )

    metrics = fixture.speaking_metrics_repo.item
    score = fixture.score_repo.item
    assert result.original_metrics["accuracy_score"] == 50
    assert result.current_metrics["accuracy_score"] == 90
    assert metrics.original_accuracy_score == 50
    assert metrics.current_accuracy_score == 90
    assert score.original_score == 50
    assert score.current_score != score.original_score
    assert score.score == score.current_score
    assert score.teacher_observation == "Ajuste docente."


def test_manual_review_allows_partial_and_makes_it_score_eligible():
    fixture = _fixture(TechnicalStatus.PARTIAL, score_eligible=False)

    result = fixture.use_case.execute(
        ManualReviewExerciseAttemptCommand(
            exercise_attempt_id=fixture.exercise_attempt_id,
            teacher_id=fixture.teacher_id,
            metrics={"accuracy_score": 90},
        )
    )

    assert result.score_eligible is True
    assert fixture.score_repo.item.technical_status == TechnicalStatus.PARTIAL
    assert "MANUAL_REVIEW_ACCEPTED_PARTIAL" in fixture.score_repo.item.quality_reasons


def test_manual_review_rejects_invalid_exercise():
    fixture = _fixture(TechnicalStatus.INVALID, score_eligible=False)

    with pytest.raises(InvalidExerciseTypeError):
        fixture.use_case.execute(
            ManualReviewExerciseAttemptCommand(
                exercise_attempt_id=fixture.exercise_attempt_id,
                teacher_id=fixture.teacher_id,
                metrics={"accuracy_score": 90},
            )
        )


class _Fixture:
    def __init__(self, technical_status: TechnicalStatus, score_eligible: bool) -> None:
        now = datetime.now(timezone.utc)
        self.teacher_id = uuid4()
        assessment_id = uuid4()
        self.exercise_attempt_id = uuid4()
        template_exercise_id = uuid4()
        exercise_id = uuid4()
        attempt_id = uuid4()
        speaking_response_id = uuid4()

        self.speaking_metrics_repo = _SingleRepo(
            SpeakingMetrics(
                id=uuid4(),
                speaking_response_id=speaking_response_id,
                pronunciation_score=50,
                accuracy_score=50,
                fluency_score=50,
                completeness_score=50,
                prosody_score=None,
                raw_speech_result_json=None,
                comparison_json={"lexical_match_percentage": 50},
                review_json=None,
                quality_json=None,
                created_at=now,
                updated_at=now,
                original_pronunciation_score=50,
                current_pronunciation_score=50,
                original_accuracy_score=50,
                current_accuracy_score=50,
                original_fluency_score=50,
                current_fluency_score=50,
                original_completeness_score=50,
                current_completeness_score=50,
                original_lexical_match=50,
                current_lexical_match=50,
            )
        )
        self.score_repo = _ScoreRepo(
            ExerciseScore(
                id=uuid4(),
                exercise_attempt_id=self.exercise_attempt_id,
                exercise_type=ExerciseType.READING_SPEAKING,
                score=50,
                score_eligible=score_eligible,
                technical_status=technical_status,
                manual_review_required=technical_status != TechnicalStatus.VALID,
                quality_reasons=[],
                scoring_components={"accuracy_score": 50},
                created_at=now,
                updated_at=now,
                original_score=50,
                current_score=50,
                original_scoring_components={"accuracy_score": 50},
                current_scoring_components={"accuracy_score": 50},
            )
        )
        self.use_case = ManualReviewExerciseAttemptUseCase(
            exercise_attempt_repo=_ByIdRepo(
                ExerciseAttempt(
                    id=self.exercise_attempt_id,
                    assessment_attempt_id=attempt_id,
                    template_exercise_id=template_exercise_id,
                    status=ExerciseAttemptStatus.ANSWERED,
                    started_at=now,
                    submitted_at=now,
                    created_at=now,
                    updated_at=now,
                )
            ),
            assessment_attempt_repo=_ByIdRepo(
                AssessmentAttempt(
                    id=attempt_id,
                    assessment_id=assessment_id,
                    student_id=uuid4(),
                    status=AttemptStatus.COMPLETED,
                    started_at=now,
                    completed_at=now,
                    created_at=now,
                    updated_at=now,
                )
            ),
            assessment_repo=_ByIdRepo(
                Assessment(
                    id=assessment_id,
                    template_id=uuid4(),
                    classroom_id=uuid4(),
                    homeroom_teacher_id=self.teacher_id,
                    title=None,
                    status=AssessmentStatus.ACTIVE,
                    scheduled_at=None,
                    created_at=now,
                    updated_at=now,
                )
            ),
            template_exercise_repo=_ByIdRepo(
                AssessmentTemplateExercise(
                    id=template_exercise_id,
                    template_id=uuid4(),
                    exercise_id=exercise_id,
                    order_index=1,
                    points=2,
                    is_required=True,
                    created_at=now,
                    updated_at=now,
                )
            ),
            exercise_repo=_ByIdRepo(
                AssessmentExercise(
                    id=exercise_id,
                    type=ExerciseType.READING_SPEAKING,
                    title="Lectura",
                    instructions=None,
                    stimulus_type=None,
                    response_type=None,
                    difficulty_level=None,
                    is_active=True,
                    created_by_teacher_id=None,
                    created_at=now,
                    updated_at=now,
                )
            ),
            exercise_score_repo=self.score_repo,
            speaking_response_repo=_ExerciseResponseRepo(
                SpeakingResponse(
                    id=speaking_response_id,
                    exercise_attempt_id=self.exercise_attempt_id,
                    audio_blob_path="audio.wav",
                    original_filename=None,
                    content_type=None,
                    duration_ms=None,
                    recognized_text=None,
                    created_at=now,
                    updated_at=now,
                )
            ),
            speaking_metrics_repo=self.speaking_metrics_repo,
            writing_response_repo=_EmptyRepo(),
            writing_metrics_repo=_EmptyRepo(),
            result_repo=_ResultRepo(),
        )


def _fixture(technical_status: TechnicalStatus, score_eligible: bool) -> _Fixture:
    return _Fixture(technical_status, score_eligible)


class _ByIdRepo:
    def __init__(self, item) -> None:
        self.item = item

    def find_by_id(self, item_id: UUID):
        return self.item if self.item.id == item_id else None


class _ExerciseResponseRepo:
    def __init__(self, item) -> None:
        self.item = item

    def find_by_exercise_attempt_id(self, exercise_attempt_id: UUID):
        return self.item if self.item.exercise_attempt_id == exercise_attempt_id else None


class _SingleRepo:
    def __init__(self, item) -> None:
        self.item = item

    def find_by_speaking_response_id(self, response_id: UUID):
        return self.item if self.item.speaking_response_id == response_id else None

    def update(self, item):
        self.item = item
        return item


class _ScoreRepo:
    def __init__(self, item: ExerciseScore) -> None:
        self.item = item

    def find_by_exercise_attempt_id(self, exercise_attempt_id: UUID) -> ExerciseScore | None:
        return self.item if self.item.exercise_attempt_id == exercise_attempt_id else None

    def find_by_assessment_attempt_id(self, attempt_id: UUID) -> list[ExerciseScore]:
        return [self.item]

    def upsert(self, score: ExerciseScore) -> ExerciseScore:
        self.item = score
        return score


class _ResultRepo:
    def find_by_attempt_id(self, attempt_id: UUID):
        return None


class _EmptyRepo:
    def __getattr__(self, name: str):
        def _missing(*args, **kwargs):
            return None

        return _missing
