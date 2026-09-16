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
from app.assessment.domain.enums import (
    AssessmentStatus,
    AttemptStatus,
    ExerciseAttemptStatus,
    ExerciseType,
    InterventionLevel,
    TechnicalStatus,
)
from app.assessment.domain.exercise import AssessmentExercise
from app.assessment.domain.metrics import AssessmentResult, ExerciseScore, SpeakingMetrics, WritingMetrics
from app.assessment.domain.response import SpeakingResponse, WritingResponse
from app.assessment.domain.template import AssessmentTemplateExercise
from app.assessment.presentation.routes import (
    _clean_scoring_snapshot,
    _current_scoring_components,
)


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
    assert score.manual_adjustment_applied is True
    assert score.manual_review_required is False
    assert score.teacher_observation == "Ajuste docente."
    assert score.adjusted_by_teacher_id == fixture.teacher_id
    assert score.adjusted_at is not None


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


def test_manual_review_high_current_final_score_without_pending_review_stays_low():
    fixture = _fixture(TechnicalStatus.VALID, score_eligible=True, with_result=True)

    result = fixture.use_case.execute(
        ManualReviewExerciseAttemptCommand(
            exercise_attempt_id=fixture.exercise_attempt_id,
            teacher_id=fixture.teacher_id,
            metrics={
                "accuracy_score": 90,
                "fluency_score": 90,
                "pronunciation_score": 90,
                "completeness_score": 90,
                "lexical_match": 90,
            },
            teacher_observation="Revisión resuelta.",
        )
    )

    updated_result = fixture.result_repo.item
    updated_score = fixture.score_repo.item
    assert result.assessment_result == {
        "original_final_score": 96.62,
        "current_final_score": 90.0,
    }
    assert updated_result.final_score == 90.0
    assert updated_result.current_final_score == 90.0
    assert updated_result.original_final_score == 96.62
    assert updated_result.intervention_level == InterventionLevel.LOW
    assert updated_result.speaking_review_required_count == 0
    assert updated_score.original_score == 50
    assert updated_score.current_score == 90.0
    assert updated_score.manual_adjustment_applied is True
    assert updated_score.manual_review_required is False

    snapshot_row = updated_result.current_scoring_snapshot_json[0]
    assert snapshot_row["scoring_components"] == snapshot_row["current_scoring_components"]
    assert snapshot_row["original_scoring_components"] == {"accuracy_score": 50}
    assert "original_scoring_components" not in snapshot_row["scoring_components"]
    assert "original_scoring_components" not in snapshot_row["current_scoring_components"]
    assert snapshot_row["current_scoring_components"]["manual_adjustment_applied"] is True
    assert snapshot_row["teacher_observation"] == "Revisión resuelta."


def test_manual_review_writing_snapshot_components_are_siblings_and_clean():
    fixture = _writing_fixture()

    fixture.use_case.execute(
        ManualReviewExerciseAttemptCommand(
            exercise_attempt_id=fixture.exercise_attempt_id,
            teacher_id=fixture.teacher_id,
            metrics={"char_accuracy": 80, "word_accuracy": 60},
            teacher_observation="Ajuste de escritura.",
        )
    )

    updated_result = fixture.result_repo.item
    updated_score = fixture.score_repo.item
    assert updated_score.original_score == 87.25
    assert updated_score.current_score == 75.0
    assert updated_score.score == updated_score.current_score
    assert updated_score.manual_adjustment_applied is True
    assert updated_score.teacher_observation == "Ajuste de escritura."
    assert updated_score.adjusted_by_teacher_id == fixture.teacher_id
    assert updated_score.adjusted_at is not None
    assert updated_result.original_final_score == 87.25
    assert updated_result.current_final_score == 75.0
    assert updated_result.final_score == 75.0

    snapshot_row = updated_result.current_scoring_snapshot_json[0]
    assert snapshot_row["scoring_components"] == snapshot_row["current_scoring_components"]
    assert snapshot_row["original_scoring_components"] == {"similarity_score": 87.25}
    assert "original_scoring_components" not in snapshot_row["scoring_components"]
    assert "original_scoring_components" not in snapshot_row["current_scoring_components"]
    assert snapshot_row["current_scoring_components"]["similarity_score"] == 75.0
    assert snapshot_row["current_scoring_components"]["manual_adjustment_applied"] is True
    assert snapshot_row["teacher_observation"] == "Ajuste de escritura."


def test_result_serialization_cleans_nested_original_components_in_snapshot_and_summaries():
    dirty_snapshot = [
        {
            "exercise_type": "READING_SPEAKING",
            "score": 88.65,
            "original_score": 97.78,
            "current_score": 88.65,
            "scoring_components": {
                "accuracy_score": 90,
                "manual_adjustment_applied": True,
                "original_scoring_components": {"accuracy_score": 97.78},
            },
            "current_scoring_components": {
                "accuracy_score": 90,
                "manual_adjustment_applied": True,
                "original_scoring_components": {"accuracy_score": 97.78},
            },
        },
        {
            "exercise_type": "READING_WRITING",
            "score": 75.0,
            "original_score": 87.25,
            "current_score": 75.0,
            "original_scoring_components": {"similarity_score": 87.25},
            "scoring_components": {
                "similarity_score": 75.0,
                "manual_adjustment_applied": True,
                "original_scoring_components": {"similarity_score": 87.25},
            },
            "current_scoring_components": {
                "similarity_score": 75.0,
                "manual_adjustment_applied": True,
                "original_scoring_components": {"similarity_score": 87.25},
            },
        },
    ]

    cleaned_snapshot = _clean_scoring_snapshot(dirty_snapshot)

    for row in cleaned_snapshot:
        assert "original_scoring_components" in row
        assert "original_scoring_components" not in row["scoring_components"]
        assert "original_scoring_components" not in row["current_scoring_components"]
        assert row["scoring_components"] == row["current_scoring_components"]

    assert cleaned_snapshot[0]["original_scoring_components"] == {"accuracy_score": 97.78}
    assert cleaned_snapshot[1]["original_scoring_components"] == {"similarity_score": 87.25}

    dirty_summary_score = ExerciseScore(
        id=uuid4(),
        exercise_attempt_id=uuid4(),
        exercise_type=ExerciseType.READING_SPEAKING,
        score=88.65,
        score_eligible=True,
        technical_status=TechnicalStatus.VALID,
        manual_review_required=False,
        quality_reasons=[],
        scoring_components={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        original_score=97.78,
        current_score=88.65,
        original_scoring_components={"accuracy_score": 97.78},
        current_scoring_components={
            "accuracy_score": 90,
            "manual_adjustment_applied": True,
            "original_scoring_components": {"accuracy_score": 97.78},
        },
    )
    summary_components = _current_scoring_components(dirty_summary_score)
    assert "original_scoring_components" not in summary_components
    assert summary_components["manual_adjustment_applied"] is True


def test_manual_review_keeps_medium_when_another_included_exercise_is_pending():
    fixture = _fixture(
        TechnicalStatus.VALID,
        score_eligible=True,
        with_result=True,
        with_pending_writing=True,
    )

    fixture.use_case.execute(
        ManualReviewExerciseAttemptCommand(
            exercise_attempt_id=fixture.exercise_attempt_id,
            teacher_id=fixture.teacher_id,
            metrics={
                "accuracy_score": 90,
                "fluency_score": 90,
                "pronunciation_score": 90,
                "completeness_score": 90,
                "lexical_match": 90,
            },
        )
    )

    assert fixture.result_repo.item.final_score == 90.0
    assert fixture.result_repo.item.intervention_level == InterventionLevel.MEDIUM
    assert fixture.result_repo.item.speaking_review_required_count == 0
    assert fixture.result_repo.item.writing_review_required_count == 1


def test_manual_review_score_threshold_can_change_intervention_level():
    fixture = _fixture(TechnicalStatus.VALID, score_eligible=True, with_result=True)

    fixture.use_case.execute(
        ManualReviewExerciseAttemptCommand(
            exercise_attempt_id=fixture.exercise_attempt_id,
            teacher_id=fixture.teacher_id,
            metrics={
                "accuracy_score": 45,
                "fluency_score": 45,
                "pronunciation_score": 45,
                "completeness_score": 45,
                "lexical_match": 45,
            },
        )
    )

    assert fixture.result_repo.item.current_final_score == 45.0
    assert fixture.result_repo.item.intervention_level == InterventionLevel.HIGH


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
    def __init__(
        self,
        technical_status: TechnicalStatus,
        score_eligible: bool,
        *,
        with_result: bool = False,
        with_pending_writing: bool = False,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.teacher_id = uuid4()
        assessment_id = uuid4()
        self.exercise_attempt_id = uuid4()
        template_exercise_id = uuid4()
        exercise_id = uuid4()
        attempt_id = uuid4()
        speaking_response_id = uuid4()
        self.attempt_id = attempt_id

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
        primary_score = ExerciseScore(
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
        exercise_attempts = [
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
        ]
        template_exercises = {
            template_exercise_id: AssessmentTemplateExercise(
                id=template_exercise_id,
                template_id=uuid4(),
                exercise_id=exercise_id,
                order_index=1,
                points=2,
                is_required=True,
                created_at=now,
                updated_at=now,
            )
        }
        exercises = {
            exercise_id: AssessmentExercise(
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
        }
        scores = [primary_score]
        if with_pending_writing:
            pending_exercise_attempt_id = uuid4()
            pending_template_exercise_id = uuid4()
            pending_exercise_id = uuid4()
            exercise_attempts.append(
                ExerciseAttempt(
                    id=pending_exercise_attempt_id,
                    assessment_attempt_id=attempt_id,
                    template_exercise_id=pending_template_exercise_id,
                    status=ExerciseAttemptStatus.EVALUATED,
                    started_at=now,
                    submitted_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
            template_exercises[pending_template_exercise_id] = AssessmentTemplateExercise(
                id=pending_template_exercise_id,
                template_id=uuid4(),
                exercise_id=pending_exercise_id,
                order_index=2,
                points=2,
                is_required=True,
                created_at=now,
                updated_at=now,
            )
            exercises[pending_exercise_id] = AssessmentExercise(
                id=pending_exercise_id,
                type=ExerciseType.READING_WRITING,
                title="Escritura",
                instructions=None,
                stimulus_type=None,
                response_type=None,
                difficulty_level=None,
                is_active=True,
                created_by_teacher_id=None,
                created_at=now,
                updated_at=now,
            )
            scores.append(
                ExerciseScore(
                    id=uuid4(),
                    exercise_attempt_id=pending_exercise_attempt_id,
                    exercise_type=ExerciseType.READING_WRITING,
                    score=90,
                    score_eligible=True,
                    technical_status=TechnicalStatus.VALID,
                    manual_review_required=True,
                    quality_reasons=["LOW_TEXT_SIMILARITY"],
                    scoring_components={"similarity_score": 90},
                    created_at=now,
                    updated_at=now,
                    original_score=90,
                    current_score=90,
                    original_scoring_components={"similarity_score": 90},
                    current_scoring_components={"similarity_score": 90},
                )
            )
        self.score_repo = _ScoreRepo(scores)
        self.result_repo = _ResultRepo(
            AssessmentResult(
                id=uuid4(),
                assessment_attempt_id=attempt_id,
                final_score=96.62,
                max_score=100.0,
                mc_correct_count=0,
                os_correct_count=0,
                speaking_completed_count=1,
                writing_completed_count=0,
                intervention_level=InterventionLevel.LOW,
                generated_at=now,
                created_at=now,
                updated_at=now,
                speaking_average_score=96.62,
                speaking_review_required_count=0,
                total_exercises=len(exercise_attempts),
                evaluated_exercises=len(exercise_attempts),
                pending_exercises=0,
                writing_average_score=None,
                writing_review_required_count=0,
                score_denominator=2,
                scoring_snapshot_json=[],
                original_final_score=96.62,
                current_final_score=96.62,
                original_scoring_snapshot_json=[],
                current_scoring_snapshot_json=[],
            )
            if with_result
            else None
        )
        self.use_case = ManualReviewExerciseAttemptUseCase(
            exercise_attempt_repo=_ExerciseAttemptRepo(exercise_attempts),
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
            template_exercise_repo=_MapRepo(template_exercises),
            exercise_repo=_MapRepo(exercises),
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
            result_repo=self.result_repo,
        )


def _fixture(
    technical_status: TechnicalStatus,
    score_eligible: bool,
    *,
    with_result: bool = False,
    with_pending_writing: bool = False,
) -> _Fixture:
    return _Fixture(
        technical_status,
        score_eligible,
        with_result=with_result,
        with_pending_writing=with_pending_writing,
    )


class _WritingFixture:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.teacher_id = uuid4()
        assessment_id = uuid4()
        self.exercise_attempt_id = uuid4()
        template_exercise_id = uuid4()
        exercise_id = uuid4()
        attempt_id = uuid4()
        writing_response_id = uuid4()

        self.writing_metrics_repo = _SingleRepo(
            WritingMetrics(
                id=uuid4(),
                writing_response_id=writing_response_id,
                confidence_avg=0.98,
                cer=0.059,
                wer=0.333,
                similarity_score=87.25,
                raw_ocr_result_json=None,
                created_at=now,
                updated_at=now,
                original_char_accuracy=94.1,
                current_char_accuracy=94.1,
                original_word_accuracy=66.7,
                current_word_accuracy=66.7,
                original_similarity_score=87.25,
                current_similarity_score=87.25,
            )
        )
        primary_score = ExerciseScore(
            id=uuid4(),
            exercise_attempt_id=self.exercise_attempt_id,
            exercise_type=ExerciseType.READING_WRITING,
            score=87.25,
            score_eligible=True,
            technical_status=TechnicalStatus.VALID,
            manual_review_required=False,
            quality_reasons=[],
            scoring_components={
                "similarity_score": 87.25,
                "original_scoring_components": {"similarity_score": 87.25},
            },
            created_at=now,
            updated_at=now,
            original_score=87.25,
            current_score=87.25,
            original_scoring_components={"similarity_score": 87.25},
            current_scoring_components={
                "similarity_score": 87.25,
                "original_scoring_components": {"similarity_score": 87.25},
            },
        )
        exercise_attempts = [
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
        ]
        self.score_repo = _ScoreRepo([primary_score])
        self.result_repo = _ResultRepo(
            AssessmentResult(
                id=uuid4(),
                assessment_attempt_id=attempt_id,
                final_score=87.25,
                max_score=100.0,
                mc_correct_count=0,
                os_correct_count=0,
                speaking_completed_count=0,
                writing_completed_count=1,
                intervention_level=InterventionLevel.LOW,
                generated_at=now,
                created_at=now,
                updated_at=now,
                speaking_average_score=None,
                speaking_review_required_count=0,
                total_exercises=1,
                evaluated_exercises=1,
                pending_exercises=0,
                writing_average_score=87.25,
                writing_review_required_count=0,
                score_denominator=2,
                scoring_snapshot_json=[],
                original_final_score=87.25,
                current_final_score=87.25,
                original_scoring_snapshot_json=[],
                current_scoring_snapshot_json=[],
            )
        )
        self.use_case = ManualReviewExerciseAttemptUseCase(
            exercise_attempt_repo=_ExerciseAttemptRepo(exercise_attempts),
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
            template_exercise_repo=_MapRepo(
                {
                    template_exercise_id: AssessmentTemplateExercise(
                        id=template_exercise_id,
                        template_id=uuid4(),
                        exercise_id=exercise_id,
                        order_index=1,
                        points=2,
                        is_required=True,
                        created_at=now,
                        updated_at=now,
                    )
                }
            ),
            exercise_repo=_MapRepo(
                {
                    exercise_id: AssessmentExercise(
                        id=exercise_id,
                        type=ExerciseType.READING_WRITING,
                        title="Escritura",
                        instructions=None,
                        stimulus_type=None,
                        response_type=None,
                        difficulty_level=None,
                        is_active=True,
                        created_by_teacher_id=None,
                        created_at=now,
                        updated_at=now,
                    )
                }
            ),
            exercise_score_repo=self.score_repo,
            speaking_response_repo=_EmptyRepo(),
            speaking_metrics_repo=_EmptyRepo(),
            writing_response_repo=_ExerciseResponseRepo(
                WritingResponse(
                    id=writing_response_id,
                    exercise_attempt_id=self.exercise_attempt_id,
                    image_blob_path="writing.png",
                    original_filename=None,
                    content_type=None,
                    recognized_text=None,
                    created_at=now,
                    updated_at=now,
                )
            ),
            writing_metrics_repo=self.writing_metrics_repo,
            result_repo=self.result_repo,
        )


def _writing_fixture() -> _WritingFixture:
    return _WritingFixture()


class _ByIdRepo:
    def __init__(self, item) -> None:
        self.item = item

    def find_by_id(self, item_id: UUID):
        return self.item if self.item.id == item_id else None


class _MapRepo:
    def __init__(self, items: dict[UUID, object]) -> None:
        self.items = items

    def find_by_id(self, item_id: UUID):
        return self.items.get(item_id)


class _ExerciseAttemptRepo:
    def __init__(self, items: list[ExerciseAttempt]) -> None:
        self.items = items

    def find_by_id(self, item_id: UUID):
        return next((item for item in self.items if item.id == item_id), None)

    def find_by_assessment_attempt_id(self, attempt_id: UUID) -> list[ExerciseAttempt]:
        return [item for item in self.items if item.assessment_attempt_id == attempt_id]


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

    def find_by_writing_response_id(self, response_id: UUID):
        return self.item if self.item.writing_response_id == response_id else None

    def update(self, item):
        self.item = item
        return item


class _ScoreRepo:
    def __init__(self, items: list[ExerciseScore]) -> None:
        self.items = items
        self.item = items[0]

    def find_by_exercise_attempt_id(self, exercise_attempt_id: UUID) -> ExerciseScore | None:
        return next((item for item in self.items if item.exercise_attempt_id == exercise_attempt_id), None)

    def find_by_assessment_attempt_id(self, attempt_id: UUID) -> list[ExerciseScore]:
        return self.items

    def upsert(self, score: ExerciseScore) -> ExerciseScore:
        self.item = score
        for index, item in enumerate(self.items):
            if item.exercise_attempt_id == score.exercise_attempt_id:
                self.items[index] = score
                break
        else:
            self.items.append(score)
        return score


class _ResultRepo:
    def __init__(self, item: AssessmentResult | None = None) -> None:
        self.item = item

    def find_by_attempt_id(self, attempt_id: UUID):
        return self.item if self.item and self.item.assessment_attempt_id == attempt_id else None

    def update(self, item: AssessmentResult) -> AssessmentResult:
        self.item = item
        return item


class _EmptyRepo:
    def __getattr__(self, name: str):
        def _missing(*args, **kwargs):
            return None

        return _missing
