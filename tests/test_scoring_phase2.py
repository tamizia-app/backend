from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.assessment.application.exceptions import (
    AttemptNotEvaluableError,
    InvalidTemplateExercisePointsError,
)
from app.assessment.application.use_cases.finish_assessment_attempt import (
    FinishAssessmentAttemptCommand,
    FinishAssessmentAttemptUseCase,
)
from app.assessment.domain.attempt import AssessmentAttempt, ExerciseAttempt
from app.assessment.domain.enums import (
    AttemptStatus,
    ExerciseAttemptStatus,
    ExerciseType,
    TechnicalStatus,
)
from app.assessment.domain.exercise import AssessmentExercise
from app.assessment.domain.metrics import AssessmentResult, ExerciseScore
from app.assessment.domain.assessment_review import determine_manual_review
from app.assessment.domain.technical_quality import calculate_reading_score, reading_quality, writing_quality
from app.assessment.domain.template import AssessmentTemplateExercise
from app.assessment.domain.writing_text_comparison import (
    calculate_similarity_score,
    determine_writing_review,
)
from app.assessment.application.ports.speech_to_text import TranscriptionResult, TranscriptionSegment
from app.iam.infrastructure.models.user_model import UserModel
from app.school.infrastructure.models.classroom_model import ClassroomModel
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
from app.school.infrastructure.models.student_model import Student, StudentConsent
from conftest import TestingSessionLocal


@pytest.fixture
def classroom_id():
    with TestingSessionLocal() as db:
        teacher = (
            db.query(HomeroomTeacherModel)
            .join(UserModel, HomeroomTeacherModel.user_id == UserModel.id)
            .filter(UserModel.email == "teacher@example.com")
            .one()
        )
        classroom = ClassroomModel(
            homeroom_teacher_id=teacher.id,
            name="Phase2",
            grade_level="primero",
            section="A",
            school_year=date(2026, 1, 1),
            is_active=True,
        )
        db.add(classroom)
        db.commit()
        return classroom.id


@pytest.fixture
def student_id(classroom_id):
    with TestingSessionLocal() as db:
        student = Student(
            classroom_id=classroom_id,
            code="PHASE2-STUDENT",
            age=7,
            gender="BOY",
            is_active=True,
        )
        db.add(student)
        db.flush()
        db.add(
            StudentConsent(
                student_id=student.id,
                status=True,
                consent_date=datetime.now(timezone.utc),
            )
        )
        db.commit()
        return student.id


def test_reading_score_phase2_all_components_present():
    score, components = calculate_reading_score(
        accuracy_score=80,
        fluency_score=60,
        pronunciation_score=90,
        completeness_score=100,
        lexical_match=70,
    )

    expected = 0.25 * 80 + 0.25 * 60 + 0.20 * 90 + 0.15 * 100 + 0.15 * 70
    assert score == pytest.approx(expected)
    assert components["formula_version"] == "phase2_v1"
    assert components["available_weight_sum"] == 1.0
    assert components["included_components"] == [
        "accuracy_score",
        "fluency_score",
        "pronunciation_score",
        "completeness_score",
        "lexical_match",
    ]


def test_reading_score_phase2_missing_lexical_renormalizes():
    score, components = calculate_reading_score(
        accuracy_score=80,
        fluency_score=60,
        pronunciation_score=90,
        completeness_score=100,
        lexical_match=None,
    )

    expected = (0.25 * 80 + 0.25 * 60 + 0.20 * 90 + 0.15 * 100) / 0.85
    assert score == pytest.approx(expected)
    assert components["available_weight_sum"] == 0.85
    assert components["excluded_components"] == ["lexical_match"]


def test_reading_score_phase2_missing_fluency_renormalizes():
    score, components = calculate_reading_score(
        accuracy_score=80,
        fluency_score=None,
        pronunciation_score=90,
        completeness_score=100,
        lexical_match=70,
    )

    expected = (0.25 * 80 + 0.20 * 90 + 0.15 * 100 + 0.15 * 70) / 0.75
    assert score == pytest.approx(expected)
    assert components["available_weight_sum"] == 0.75
    assert components["excluded_components"] == ["fluency_score"]


def test_reading_score_phase2_all_none_returns_none():
    score, components = calculate_reading_score(
        accuracy_score=None,
        fluency_score=None,
        pronunciation_score=None,
        completeness_score=None,
        lexical_match=None,
    )

    assert score is None
    assert components["available_weight_sum"] == 0
    assert components["included_components"] == []


def test_reading_score_phase2_fluency_participates():
    low_fluency, _ = calculate_reading_score(
        accuracy_score=80,
        fluency_score=20,
        pronunciation_score=80,
        completeness_score=80,
        lexical_match=80,
    )
    high_fluency, _ = calculate_reading_score(
        accuracy_score=80,
        fluency_score=100,
        pronunciation_score=80,
        completeness_score=80,
        lexical_match=80,
    )

    assert high_fluency > low_fluency


def test_writing_score_keeps_75_25_formula():
    assert calculate_similarity_score(cer=0.20, wer=0.50) == 72.5


def test_writing_ocr_confidence_does_not_change_numeric_score():
    high_confidence = determine_writing_review("El gato duerme.", "El gato duerme.", confidence_avg=0.95)
    low_confidence = determine_writing_review("El gato duerme.", "El gato duerme.", confidence_avg=0.50)

    assert high_confidence.similarity_score == low_confidence.similarity_score == 100.0
    assert low_confidence.review_required is True


def test_speaking_low_performance_reasons_are_score_eligible_not_invalid():
    quality = reading_quality(
        {
            "status": "completed",
            "recognized_text": "el sol brilla que",
            "assessment_recognized_text": "el sol brilla que",
            "review": {
                "required": True,
                "reasons": [
                    "HIGH_WORD_ERROR_RATE",
                    "LOW_LEXICAL_MATCH",
                    "LOW_ACCURACY_SCORE",
                ],
            },
        },
        score=25.0,
    )

    assert quality.technical_status == TechnicalStatus.VALID
    assert quality.score_eligible is True
    assert quality.manual_review_required is True


def test_speaking_extra_words_are_review_reasons_not_technical_invalidity():
    review = determine_manual_review(
        TranscriptionResult(
            text="el sol brilla que",
            language="es",
            language_probability=0.99,
            duration_seconds=2.0,
            segments=[
                TranscriptionSegment(
                    text="el sol brilla que",
                    start_seconds=0.0,
                    end_seconds=2.0,
                    avg_logprob=-0.1,
                    no_speech_prob=0.01,
                    words=[],
                )
            ],
            provider="test",
            model="test",
        ),
        azure_text="el sol brilla que",
        audio_duration_seconds=2.0,
        low_logprob_threshold=-1.0,
        comparison={
            "wer_percentage": 300.0,
            "lexical_match_percentage": 100.0,
            "insertions": 3,
            "omissions": 0,
        },
    )
    quality = reading_quality(
        {
            "status": "completed",
            "recognized_text": "el sol brilla que",
            "review": review,
        },
        score=45.0,
    )

    assert "EXTRA_WORDS_DETECTED" in review["reasons"]
    assert "HIGH_WORD_ERROR_RATE" in review["reasons"]
    assert quality.technical_status == TechnicalStatus.VALID
    assert quality.score_eligible is True


def test_writing_low_similarity_with_ocr_text_is_score_eligible_not_invalid():
    quality = writing_quality(
        recognized_text="texto muy distinto",
        confidence_avg=0.95,
        score=20.0,
        review_required=True,
        review_reasons=["LOW_TEXT_SIMILARITY", "HIGH_CHARACTER_ERROR_RATE"],
    )

    assert quality.technical_status == TechnicalStatus.VALID
    assert quality.score_eligible is True
    assert quality.manual_review_required is True


@pytest.mark.parametrize("points", [1, 2, 3])
def test_attach_exercise_accepts_phase2_points(client, teacher_headers, points):
    template_id, exercise_id = _create_template_and_mc_exercise(client, teacher_headers)

    response = client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "points": points, "is_required": True},
    )

    assert response.status_code == 201


@pytest.mark.parametrize("points", [0, -1, 4])
def test_attach_exercise_rejects_invalid_phase2_points(client, teacher_headers, points):
    template_id, exercise_id = _create_template_and_mc_exercise(client, teacher_headers)

    response = client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "points": points, "is_required": True},
    )

    assert response.status_code == 422


def test_attach_exercise_default_points_is_valid(client, teacher_headers):
    template_id, exercise_id = _create_template_and_mc_exercise(client, teacher_headers)

    response = client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "is_required": True},
    )

    assert response.status_code == 201


def test_final_score_uses_weighted_points_and_snapshot_traceability():
    uc = _finish_use_case(
        [
            _row(ExerciseType.MULTIPLE_CHOICE, score=100, points=1),
            _row(ExerciseType.MULTIPLE_CHOICE, score=100, points=2),
            _row(ExerciseType.ORDER_SYLLABLES, score=100, points=2),
            _row(ExerciseType.READING_SPEAKING, score=40, points=3),
            _row(ExerciseType.READING_WRITING, score=40, points=3),
        ]
    )

    result = uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    assert result.final_score == 67.27
    assert result.score_denominator == 11
    assert result.max_score == 100.0
    row = result.scoring_snapshot_json[0]
    assert row["scoring_version"] == "phase2_v1"
    assert row["points"] == 1
    assert row["weighted_contribution"] == 100
    assert row["effective_weight"] == 1
    assert row["included_weight_sum"] == 11
    assert row["coverage_weight_percentage"] == 100.0
    assert row["final_scoring_formula"] == "weighted_mean_by_template_exercise_points"
    assert row["intervention_level_status"] == "provisional"


def test_final_score_uses_current_scores_and_initializes_original_current_result():
    uc = _finish_use_case(
        [
            _row(ExerciseType.READING_SPEAKING, score=40, current_score=90, points=1),
            _row(ExerciseType.READING_WRITING, score=40, current_score=80, points=3),
        ]
    )

    result = uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    assert result.final_score == 82.5
    assert result.original_final_score == 82.5
    assert result.current_final_score == 82.5
    assert result.scoring_snapshot_json[0]["original_score"] == 40
    assert result.scoring_snapshot_json[0]["current_score"] == 90
    assert result.original_scoring_snapshot_json == result.scoring_snapshot_json
    assert result.current_scoring_snapshot_json == result.scoring_snapshot_json


def test_invalid_exercise_is_excluded_when_coverage_and_domains_are_sufficient():
    uc = _finish_use_case(
        [
            _row(ExerciseType.READING_SPEAKING, score=90, points=3, is_required=True),
            _row(ExerciseType.READING_WRITING, score=80, points=3, is_required=True),
            _row(ExerciseType.MULTIPLE_CHOICE, score=100, points=3, is_required=True),
            _row(
                ExerciseType.MULTIPLE_CHOICE,
                score=None,
                points=1,
                is_required=True,
                score_eligible=False,
                technical_status=TechnicalStatus.INVALID,
            ),
        ]
    )

    result = uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    assert result.final_score == 90.0
    assert result.score_denominator == 9
    assert result.evaluated_exercises == 3
    excluded = next(row for row in result.scoring_snapshot_json if not row["included"])
    assert excluded["exclusion_reason"] == "NOT_SCORE_ELIGIBLE"
    assert excluded["included_weight_sum"] == 9
    assert excluded["total_template_weight_sum"] == 10
    assert excluded["coverage_weight_percentage"] == 90.0
    assert excluded["invalid_or_excluded_exercise_count"] == 1
    assert excluded["result_status"] == "COMPLETED_WITH_WARNINGS"
    assert excluded["has_warnings"] is True
    assert "INVALID_EXERCISES" in excluded["warning_reasons"]
    assert result.intervention_level.value == "LOW"


def test_high_final_score_with_manual_review_warning_keeps_low_intervention():
    uc = _finish_use_case(
        [
            _row(
                ExerciseType.READING_SPEAKING,
                score=85,
                points=3,
                technical_status=TechnicalStatus.PARTIAL,
                manual_review_required=True,
                quality_reasons=[
                    "ASR_AZURE_TRANSCRIPT_DIVERGENCE",
                    "HIGH_WORD_ERROR_RATE",
                    "LOW_LEXICAL_MATCH",
                ],
            ),
            _row(ExerciseType.READING_WRITING, score=100, points=3),
            _row(ExerciseType.MULTIPLE_CHOICE, score=100, points=3),
        ]
    )

    result = uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    assert result.final_score == 95.0
    assert result.intervention_level.value == "LOW"
    row = result.scoring_snapshot_json[0]
    assert row["result_status"] == "COMPLETED_WITH_WARNINGS"
    assert row["has_warnings"] is True
    assert row["partial_exercise_count"] == 1
    assert "PARTIAL_EXERCISES" in row["warning_reasons"]
    assert "MANUAL_REVIEW_REQUIRED" in row["warning_reasons"]


def test_medium_final_score_uses_score_threshold_only():
    uc = _finish_use_case(
        [
            _row(ExerciseType.READING_SPEAKING, score=70, points=3),
            _row(ExerciseType.READING_WRITING, score=70, points=3),
            _row(
                ExerciseType.MULTIPLE_CHOICE,
                score=70,
                points=3,
                manual_review_required=True,
                quality_reasons=["LOW_TEXT_SIMILARITY"],
            ),
        ]
    )

    result = uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    assert result.final_score == 70.0
    assert result.intervention_level.value == "MEDIUM"
    assert result.scoring_snapshot_json[0]["result_status"] == "COMPLETED_WITH_WARNINGS"


def test_low_scores_with_technical_evidence_finish_with_high_intervention():
    uc = _finish_use_case(
        [
            _row(ExerciseType.READING_SPEAKING, score=10, points=3),
            _row(ExerciseType.READING_WRITING, score=20, points=3),
            _row(ExerciseType.MULTIPLE_CHOICE, score=30, points=3),
        ]
    )

    result = uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    assert result.final_score == 20.0
    assert result.intervention_level.value == "HIGH"


def test_required_partial_with_score_is_included_and_warns():
    uc = _finish_use_case(
        [
            _row(
                ExerciseType.READING_SPEAKING,
                score=40,
                points=3,
                score_eligible=False,
                technical_status=TechnicalStatus.PARTIAL,
                manual_review_required=True,
                quality_reasons=["LOW_ASR_QUALITY"],
            ),
            _row(ExerciseType.READING_WRITING, score=80, points=3),
            _row(ExerciseType.MULTIPLE_CHOICE, score=100, points=3),
        ]
    )

    result = uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    partial = next(row for row in result.scoring_snapshot_json if row["technical_status"] == "PARTIAL")
    assert partial["included"] is True
    assert partial["effective_weight"] == 3
    assert result.score_denominator == 9
    assert partial["result_status"] == "COMPLETED_WITH_WARNINGS"
    assert "PARTIAL_EXERCISES" in partial["warning_reasons"]


def test_required_partial_without_score_is_excluded_if_global_evidence_is_sufficient():
    uc = _finish_use_case(
        [
            _row(ExerciseType.READING_SPEAKING, score=80, points=3),
            _row(ExerciseType.READING_WRITING, score=80, points=3),
            _row(ExerciseType.MULTIPLE_CHOICE, score=100, points=3),
            _row(
                ExerciseType.MULTIPLE_CHOICE,
                score=None,
                points=1,
                score_eligible=False,
                technical_status=TechnicalStatus.PARTIAL,
                manual_review_required=True,
                quality_reasons=["PARTIAL_EVALUATION"],
            ),
        ]
    )

    result = uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    excluded = next(row for row in result.scoring_snapshot_json if not row["included"])
    assert excluded["technical_status"] == "PARTIAL"
    assert excluded["exclusion_reason"] == "NOT_SCORE_ELIGIBLE"
    assert excluded["coverage_weight_percentage"] == 90.0
    assert "PARTIAL_EXERCISES" in excluded["warning_reasons"]


def test_finish_blocks_when_score_coverage_is_below_threshold():
    uc = _finish_use_case(
        [
            _row(ExerciseType.READING_SPEAKING, score=80, points=1),
            _row(
                ExerciseType.READING_WRITING,
                score=None,
                points=3,
                score_eligible=False,
                technical_status=TechnicalStatus.INVALID,
            ),
        ]
    )

    with pytest.raises(AttemptNotEvaluableError) as exc:
        uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    assert exc.value.detail["reason"] == "insufficient_score_coverage"
    assert exc.value.detail["coverage_weight_percentage"] == 25.0


def test_finish_blocks_when_template_has_no_evaluable_speaking():
    uc = _finish_use_case(
        [
            _row(
                ExerciseType.READING_SPEAKING,
                score=None,
                points=1,
                score_eligible=False,
                technical_status=TechnicalStatus.INVALID,
            ),
            _row(ExerciseType.READING_WRITING, score=80, points=3),
            _row(ExerciseType.MULTIPLE_CHOICE, score=100, points=3),
            _row(ExerciseType.MULTIPLE_CHOICE, score=100, points=3),
        ]
    )

    with pytest.raises(AttemptNotEvaluableError) as exc:
        uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    assert exc.value.detail["reason"] == "no_speaking_evidence"


def test_finish_blocks_when_template_has_no_evaluable_writing():
    uc = _finish_use_case(
        [
            _row(ExerciseType.READING_SPEAKING, score=80, points=3),
            _row(
                ExerciseType.READING_WRITING,
                score=None,
                points=1,
                score_eligible=False,
                technical_status=TechnicalStatus.INVALID,
            ),
            _row(ExerciseType.MULTIPLE_CHOICE, score=100, points=3),
            _row(ExerciseType.MULTIPLE_CHOICE, score=100, points=3),
        ]
    )

    with pytest.raises(AttemptNotEvaluableError) as exc:
        uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))

    assert exc.value.detail["reason"] == "no_writing_evidence"


def test_required_invalid_blocks_final_score():
    uc = _finish_use_case(
        [
            _row(
                ExerciseType.MULTIPLE_CHOICE,
                score=None,
                points=2,
                is_required=True,
                score_eligible=False,
                technical_status=TechnicalStatus.INVALID,
            )
        ]
    )

    with pytest.raises(AttemptNotEvaluableError):
        uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))


def test_legacy_points_are_rejected_before_final_score():
    uc = _finish_use_case([_row(ExerciseType.MULTIPLE_CHOICE, score=100, points=10)])

    with pytest.raises(InvalidTemplateExercisePointsError):
        uc.execute(FinishAssessmentAttemptCommand(attempt_id=uc.attempt_id))


def test_finish_get_result_and_review_expose_phase2_scoring_contract(
    client, teacher_headers, classroom_id, student_id
):
    template = client.post(
        "/api/v1/assessments/templates",
        headers=teacher_headers,
        json={"name": "Phase 2 API contract", "version": 1},
    ).json()
    first_exercise_id = _create_mc_exercise(client, teacher_headers, "MC one")
    second_exercise_id = _create_mc_exercise(client, teacher_headers, "MC two")

    for exercise_id, index, points in (
        (first_exercise_id, 1, 1),
        (second_exercise_id, 2, 3),
    ):
        response = client.post(
            f"/api/v1/assessments/templates/{template['template_id']}/exercises",
            headers=teacher_headers,
            json={
                "exercise_id": exercise_id,
                "order_index": index,
                "points": points,
                "is_required": True,
            },
        )
        assert response.status_code == 201

    attempt_id = _start_attempt(client, teacher_headers, classroom_id, student_id, template["template_id"])
    detail = client.get(f"/api/v1/assessments/attempts/{attempt_id}", headers=teacher_headers).json()
    for item in detail["exercise_attempts"]:
        option_id = item["exercise"]["mc_question"]["options"][0]["option_id"]
        response = client.post(
            f"/api/v1/assessments/exercise-attempts/{item['exercise_attempt_id']}/mc-response",
            headers=teacher_headers,
            json={"selected_option_id": option_id},
        )
        assert response.status_code == 200

    finish = client.post(
        f"/api/v1/assessments/attempts/{attempt_id}/finish", headers=teacher_headers
    )
    assert finish.status_code == 200
    finish_payload = finish.json()
    _assert_phase2_contract(
        finish_payload,
        included_weight_sum=4,
        total_template_weight_sum=4,
        coverage_weight_percentage=100.0,
        included_exercise_count=2,
        total_exercise_count=2,
        invalid_or_excluded_exercise_count=0,
    )

    result_payload = client.get(
        f"/api/v1/assessments/attempts/{attempt_id}/result", headers=teacher_headers
    ).json()
    _assert_phase2_contract(
        result_payload,
        included_weight_sum=4,
        total_template_weight_sum=4,
        coverage_weight_percentage=100.0,
        included_exercise_count=2,
        total_exercise_count=2,
        invalid_or_excluded_exercise_count=0,
    )

    review_payload = client.get(
        f"/api/v1/assessments/attempts/{attempt_id}/review", headers=teacher_headers
    ).json()
    _assert_phase2_contract(
        review_payload["result"],
        included_weight_sum=4,
        total_template_weight_sum=4,
        coverage_weight_percentage=100.0,
        included_exercise_count=2,
        total_exercise_count=2,
        invalid_or_excluded_exercise_count=0,
    )


def test_low_coverage_response_returns_structured_not_interpretable_error(
    client, teacher_headers, classroom_id, student_id
):
    template = client.post(
        "/api/v1/assessments/templates",
        headers=teacher_headers,
        json={"name": "Phase 2 optional coverage", "version": 1},
    ).json()
    required_exercise_id = _create_mc_exercise(client, teacher_headers, "Required MC")
    optional_exercise_id = _create_mc_exercise(client, teacher_headers, "Optional MC")

    for exercise_id, index, points, required in (
        (required_exercise_id, 1, 1, True),
        (optional_exercise_id, 2, 3, False),
    ):
        response = client.post(
            f"/api/v1/assessments/templates/{template['template_id']}/exercises",
            headers=teacher_headers,
            json={
                "exercise_id": exercise_id,
                "order_index": index,
                "points": points,
                "is_required": required,
            },
        )
        assert response.status_code == 201

    attempt_id = _start_attempt(client, teacher_headers, classroom_id, student_id, template["template_id"])
    detail = client.get(f"/api/v1/assessments/attempts/{attempt_id}", headers=teacher_headers).json()
    required_item = detail["exercise_attempts"][0]
    option_id = required_item["exercise"]["mc_question"]["options"][0]["option_id"]
    client.post(
        f"/api/v1/assessments/exercise-attempts/{required_item['exercise_attempt_id']}/mc-response",
        headers=teacher_headers,
        json={"selected_option_id": option_id},
    )

    finish = client.post(
        f"/api/v1/assessments/attempts/{attempt_id}/finish", headers=teacher_headers
    )
    assert finish.status_code == 409
    detail = finish.json()["detail"]
    assert detail["code"] == "ASSESSMENT_NOT_INTERPRETABLE"
    assert detail["reason"] == "insufficient_score_coverage"
    assert detail["included_weight_sum"] == 1
    assert detail["total_template_weight_sum"] == 4
    assert detail["coverage_weight_percentage"] == 25.0


def test_required_invalid_returns_structured_not_interpretable_error(
    client, teacher_headers, classroom_id, student_id
):
    template_id, exercise_id = _create_template_and_mc_exercise(client, teacher_headers)
    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "points": 2, "is_required": True},
    )
    attempt_id = _start_attempt(client, teacher_headers, classroom_id, student_id, template_id)

    finish = client.post(
        f"/api/v1/assessments/attempts/{attempt_id}/finish", headers=teacher_headers
    )

    assert finish.status_code == 409
    detail = finish.json()["detail"]
    assert detail["code"] == "ASSESSMENT_NOT_INTERPRETABLE"
    assert detail["reason"] == "insufficient_score_coverage"
    assert detail["scoring_version"] == "phase2_v1"
    assert detail["coverage_weight_percentage"] == 0.0
    assert "resultado global interpretable" in detail["message"]

    result = client.get(
        f"/api/v1/assessments/attempts/{attempt_id}/result", headers=teacher_headers
    )
    assert result.status_code == 404


def _create_template_and_mc_exercise(client, headers) -> tuple[str, str]:
    template = client.post(
        "/api/v1/assessments/templates",
        headers=headers,
        json={"name": "Phase 2 template", "version": 1},
    ).json()
    exercise = client.post(
        "/api/v1/assessments/exercises",
        headers=headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC phase 2",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()
    return template["template_id"], exercise["exercise_id"]


def _create_mc_exercise(client, headers, title: str) -> str:
    response = client.post(
        "/api/v1/assessments/exercises",
        headers=headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": title,
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    )
    assert response.status_code == 201
    return response.json()["exercise_id"]


def _start_attempt(client, headers, classroom_id, student_id, template_id: str) -> str:
    assessment = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()
    attempt = client.post(
        f"/api/v1/assessments/{assessment['assessment_id']}/attempts",
        headers=headers,
        json={"student_id": str(student_id)},
    ).json()
    return attempt["attempt_id"]


def _assert_phase2_contract(
    payload: dict,
    *,
    included_weight_sum: float,
    total_template_weight_sum: float,
    coverage_weight_percentage: float,
    included_exercise_count: int,
    total_exercise_count: int,
    invalid_or_excluded_exercise_count: int,
) -> None:
    assert payload["scoring_version"] == "phase2_v1"
    assert payload["final_scoring_formula"] == "weighted_mean_by_template_exercise_points"
    assert payload["included_weight_sum"] == included_weight_sum
    assert payload["total_template_weight_sum"] == total_template_weight_sum
    assert payload["coverage_weight_percentage"] == coverage_weight_percentage
    assert payload["included_exercise_count"] == included_exercise_count
    assert payload["total_exercise_count"] == total_exercise_count
    assert payload["invalid_or_excluded_exercise_count"] == invalid_or_excluded_exercise_count
    assert payload["score_denominator"] == included_weight_sum
    assert payload["score_denominator_type"] == "included_weight_sum"
    assert payload["score_denominator_deprecated"] is True


def _row(
    exercise_type: ExerciseType,
    *,
    score: float | None,
    points: int,
    current_score: float | None = None,
    is_required: bool = True,
    score_eligible: bool = True,
    technical_status: TechnicalStatus = TechnicalStatus.VALID,
    manual_review_required: bool = False,
    quality_reasons: list[str] | None = None,
) -> dict:
    return {
        "exercise_attempt_id": uuid4(),
        "template_exercise_id": uuid4(),
        "exercise_id": uuid4(),
        "exercise_type": exercise_type,
        "score": score,
        "current_score": current_score,
        "points": points,
        "is_required": is_required,
        "score_eligible": score_eligible,
        "technical_status": technical_status,
        "manual_review_required": manual_review_required,
        "quality_reasons": quality_reasons or [],
    }


def _finish_use_case(rows: list[dict]) -> FinishAssessmentAttemptUseCase:
    now = datetime.now(timezone.utc)
    attempt_id = uuid4()
    attempt = AssessmentAttempt(
        id=attempt_id,
        assessment_id=uuid4(),
        student_id=uuid4(),
        status=AttemptStatus.IN_PROGRESS,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    exercise_attempts = []
    template_exercises = {}
    exercises = {}
    scores = []

    for index, row in enumerate(rows, start=1):
        exercise_attempts.append(
            ExerciseAttempt(
                id=row["exercise_attempt_id"],
                assessment_attempt_id=attempt_id,
                template_exercise_id=row["template_exercise_id"],
                status=ExerciseAttemptStatus.EVALUATED,
                started_at=now,
                submitted_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        template_exercises[row["template_exercise_id"]] = AssessmentTemplateExercise(
            id=row["template_exercise_id"],
            template_id=uuid4(),
            exercise_id=row["exercise_id"],
            order_index=index,
            points=row["points"],
            is_required=row["is_required"],
            created_at=now,
            updated_at=now,
        )
        exercises[row["exercise_id"]] = AssessmentExercise(
            id=row["exercise_id"],
            type=row["exercise_type"],
            title=f"Exercise {index}",
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
                exercise_attempt_id=row["exercise_attempt_id"],
                exercise_type=row["exercise_type"],
                score=row["score"],
                score_eligible=row["score_eligible"],
                technical_status=row["technical_status"],
                manual_review_required=row["manual_review_required"],
                quality_reasons=row["quality_reasons"],
                scoring_components={"is_correct": row["score"] == 100},
                created_at=now,
                updated_at=now,
                original_score=row["score"],
                current_score=row["current_score"] if row["current_score"] is not None else row["score"],
                original_scoring_components={"is_correct": row["score"] == 100},
                current_scoring_components={
                    "is_correct": (
                        row["current_score"] if row["current_score"] is not None else row["score"]
                    )
                    == 100
                },
            )
        )

    uc = FinishAssessmentAttemptUseCase(
        attempt_repo=_AttemptRepo(attempt),
        exercise_attempt_repo=_ExerciseAttemptRepo(exercise_attempts),
        template_exercise_repo=_ByIdRepo(template_exercises),
        exercise_repo=_ByIdRepo(exercises),
        exercise_score_repo=_ScoreRepo(scores),
        result_repo=_ResultRepo(),
    )
    uc.attempt_id = attempt_id
    return uc


class _AttemptRepo:
    def __init__(self, attempt: AssessmentAttempt) -> None:
        self.attempt = attempt

    def find_by_id(self, attempt_id: UUID) -> AssessmentAttempt | None:
        return self.attempt if self.attempt.id == attempt_id else None

    def update(self, attempt: AssessmentAttempt) -> AssessmentAttempt:
        self.attempt = replace(attempt)
        return attempt


class _ExerciseAttemptRepo:
    def __init__(self, exercise_attempts: list[ExerciseAttempt]) -> None:
        self.exercise_attempts = exercise_attempts

    def find_by_assessment_attempt_id(self, attempt_id: UUID) -> list[ExerciseAttempt]:
        return [
            exercise_attempt
            for exercise_attempt in self.exercise_attempts
            if exercise_attempt.assessment_attempt_id == attempt_id
        ]


class _ByIdRepo:
    def __init__(self, items: dict[UUID, object]) -> None:
        self.items = items

    def find_by_id(self, item_id: UUID):
        return self.items.get(item_id)


class _ScoreRepo:
    def __init__(self, scores: list[ExerciseScore]) -> None:
        self.scores = scores

    def find_by_assessment_attempt_id(self, attempt_id: UUID) -> list[ExerciseScore]:
        return self.scores


class _ResultRepo:
    def create(self, result: AssessmentResult) -> AssessmentResult:
        return result
