from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from app.assessment.domain.enums import (
    AssessmentStatus,
    AttemptStatus,
    ExerciseAttemptStatus,
)
from app.assessment.infrastructure.models.assessment_model import AssessmentModel
from app.assessment.infrastructure.models.attempt_model import (
    AssessmentAttemptModel,
    ExerciseAttemptModel,
)
from app.assessment.infrastructure.models.exercise_model import AssessmentExerciseModel
from app.assessment.infrastructure.models.template_model import (
    AssessmentTemplateExerciseModel,
    AssessmentTemplateModel,
)
from app.core.config import Settings
from app.iam.infrastructure.models.user_model import UserModel
from app.school.infrastructure.models.classroom_model import ClassroomModel
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
from app.school.infrastructure.models.student_model import Student, StudentConsent
from conftest import TestingSessionLocal
from scripts.admin import reset_demo_assessment_data


def test_deactivate_template_with_attempts_keeps_history(client, teacher_headers):
    template_id, _, template_exercise_id = _create_attached_template(client, teacher_headers)
    _, attempt_id, exercise_attempt_id = _create_history(template_id, template_exercise_id)

    response = client.patch(
        f"/api/v1/assessments/templates/{template_id}/deactivate",
        headers=teacher_headers,
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    with TestingSessionLocal() as db:
        assert db.get(AssessmentAttemptModel, attempt_id) is not None
        assert db.get(ExerciseAttemptModel, exercise_attempt_id) is not None


def test_deactivate_template_not_found(client, teacher_headers):
    response = client.patch(
        f"/api/v1/assessments/templates/{uuid4()}/deactivate",
        headers=teacher_headers,
    )

    assert response.status_code == 404


def test_activate_template_sets_active_true(client, teacher_headers):
    template_id, _, _ = _create_attached_template(client, teacher_headers)
    assert client.patch(
        f"/api/v1/assessments/templates/{template_id}/deactivate",
        headers=teacher_headers,
    ).status_code == 200

    response = client.patch(
        f"/api/v1/assessments/templates/{template_id}/activate",
        headers=teacher_headers,
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_delete_template_without_attempts_deletes_relation_not_global_exercise(client, teacher_headers):
    template_id, exercise_id, template_exercise_id = _create_attached_template(client, teacher_headers)

    response = client.delete(
        f"/api/v1/assessments/templates/{template_id}",
        headers=teacher_headers,
    )

    assert response.status_code == 204
    with TestingSessionLocal() as db:
        assert db.get(AssessmentTemplateModel, UUID(template_id)) is None
        assert db.get(AssessmentTemplateExerciseModel, template_exercise_id) is None
        assert db.get(AssessmentExerciseModel, UUID(exercise_id)) is not None


def test_delete_template_with_attempts_returns_structured_409(client, teacher_headers):
    template_id, _, template_exercise_id = _create_attached_template(client, teacher_headers)
    _create_history(template_id, template_exercise_id)

    response = client.delete(
        f"/api/v1/assessments/templates/{template_id}",
        headers=teacher_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "TEMPLATE_HAS_HISTORY"
    with TestingSessionLocal() as db:
        assert db.get(AssessmentTemplateModel, UUID(template_id)) is not None


def test_invalid_points_listing_includes_legacy_and_excludes_valid(client, teacher_headers):
    template_id, _, template_exercise_id = _create_attached_template(client, teacher_headers)
    _create_attached_template(client, teacher_headers, name="Valid points")
    with TestingSessionLocal() as db:
        db.execute(text("PRAGMA ignore_check_constraints = ON"))
        row = db.get(AssessmentTemplateExerciseModel, template_exercise_id)
        row.points = 10
        db.commit()
        db.execute(text("PRAGMA ignore_check_constraints = OFF"))

    response = client.get(
        "/api/v1/assessments/admin/templates/invalid-points",
        headers=teacher_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["template_id"] == template_id
    assert data[0]["current_points"] == 10
    assert data[0]["reason"] == "points_out_of_phase2_range"


@pytest.mark.parametrize("points", [1, 2, 3])
def test_update_template_exercise_points_accepts_phase2_values(client, teacher_headers, points):
    template_id, _, template_exercise_id = _create_attached_template(client, teacher_headers)

    response = client.patch(
        f"/api/v1/assessments/templates/{template_id}/exercises/{template_exercise_id}/points",
        headers=teacher_headers,
        json={"points": points},
    )

    assert response.status_code == 200
    assert response.json()["points"] == points


@pytest.mark.parametrize("points", [0, -1, 4])
def test_update_template_exercise_points_rejects_invalid_values(client, teacher_headers, points):
    template_id, _, template_exercise_id = _create_attached_template(client, teacher_headers)

    response = client.patch(
        f"/api/v1/assessments/templates/{template_id}/exercises/{template_exercise_id}/points",
        headers=teacher_headers,
        json={"points": points},
    )

    assert response.status_code == 422


def test_update_template_exercise_points_wrong_template_fails(client, teacher_headers):
    _, _, template_exercise_id = _create_attached_template(client, teacher_headers)
    other_template = client.post(
        "/api/v1/assessments/templates",
        headers=teacher_headers,
        json={"name": "Other template", "version": 1},
    ).json()

    response = client.patch(
        f"/api/v1/assessments/templates/{other_template['template_id']}/exercises/{template_exercise_id}/points",
        headers=teacher_headers,
        json={"points": 1},
    )

    assert response.status_code == 404


def test_reset_demo_script_dry_run_does_not_modify_data(capsys):
    template_id = _create_template_model("DemoReset dry", active=True)
    args = _reset_args(confirm=True, execute=False, template_name_prefix="DemoReset")

    exit_code = reset_demo_assessment_data.run(
        args,
        session_factory=TestingSessionLocal,
        settings=Settings(environment="local"),
    )

    assert exit_code == 0
    assert "DRY-RUN" in capsys.readouterr().out
    with TestingSessionLocal() as db:
        assert db.get(AssessmentTemplateModel, template_id) is not None


def test_reset_demo_script_requires_confirmation(capsys):
    args = _reset_args(confirm=False, execute=True, template_name_prefix="DemoReset")

    exit_code = reset_demo_assessment_data.run(
        args,
        session_factory=TestingSessionLocal,
        settings=Settings(environment="local"),
    )

    assert exit_code == 2
    assert "confirm" in capsys.readouterr().out


def test_reset_demo_script_execute_filter_only_deletes_matching_no_history():
    target_id = _create_template_model("DemoReset target", active=True)
    other_id = _create_template_model("Other target", active=True)
    args = _reset_args(confirm=True, execute=True, template_name_prefix="DemoReset")

    exit_code = reset_demo_assessment_data.run(
        args,
        session_factory=TestingSessionLocal,
        settings=Settings(environment="local"),
    )

    assert exit_code == 0
    with TestingSessionLocal() as db:
        assert db.get(AssessmentTemplateModel, target_id) is None
        assert db.get(AssessmentTemplateModel, other_id) is not None


def test_reset_demo_script_does_not_delete_templates_with_history():
    template_id = _create_template_model("DemoReset history", active=True)
    exercise_id = _create_exercise_model("DemoReset history exercise")
    template_exercise_id = _create_template_exercise_model(template_id, exercise_id)
    _, attempt_id, _ = _create_history(str(template_id), template_exercise_id)
    args = _reset_args(confirm=True, execute=True, template_name_prefix="DemoReset")

    exit_code = reset_demo_assessment_data.run(
        args,
        session_factory=TestingSessionLocal,
        settings=Settings(environment="local"),
    )

    assert exit_code == 0
    with TestingSessionLocal() as db:
        template = db.get(AssessmentTemplateModel, template_id)
        assert template is not None
        assert template.is_active is False
        assert db.get(AssessmentAttemptModel, attempt_id) is not None


def _create_attached_template(client, headers, *, name: str = "Admin template") -> tuple[str, str, UUID]:
    template = client.post(
        "/api/v1/assessments/templates",
        headers=headers,
        json={"name": name, "version": 1},
    ).json()
    exercise = client.post(
        "/api/v1/assessments/exercises",
        headers=headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": f"{name} exercise",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()
    response = client.post(
        f"/api/v1/assessments/templates/{template['template_id']}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise["exercise_id"],
            "order_index": 1,
            "points": 2,
            "is_required": True,
        },
    )
    assert response.status_code == 201
    with TestingSessionLocal() as db:
        template_exercise_id = db.scalar(
            select(AssessmentTemplateExerciseModel.id).where(
                AssessmentTemplateExerciseModel.template_id == UUID(template["template_id"])
            )
        )
    return template["template_id"], exercise["exercise_id"], template_exercise_id


def _create_history(template_id: str, template_exercise_id: UUID) -> tuple[UUID, UUID, UUID]:
    with TestingSessionLocal() as db:
        teacher_id = _teacher_id(db)
        classroom = ClassroomModel(
            homeroom_teacher_id=teacher_id,
            name=f"Admin {uuid4()}",
            grade_level="primero",
            section="A",
            school_year=date(2026, 1, 1),
            is_active=True,
        )
        db.add(classroom)
        db.flush()
        student = Student(
            classroom_id=classroom.id,
            code=f"ST-{uuid4()}",
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
                consent_date=datetime.now(UTC),
            )
        )
        assessment = AssessmentModel(
            template_id=UUID(template_id),
            classroom_id=classroom.id,
            homeroom_teacher_id=teacher_id,
            status=AssessmentStatus.ACTIVE,
        )
        db.add(assessment)
        db.flush()
        attempt = AssessmentAttemptModel(
            assessment_id=assessment.id,
            student_id=student.id,
            status=AttemptStatus.IN_PROGRESS,
            started_at=datetime.now(UTC),
        )
        db.add(attempt)
        db.flush()
        exercise_attempt = ExerciseAttemptModel(
            assessment_attempt_id=attempt.id,
            template_exercise_id=template_exercise_id,
            status=ExerciseAttemptStatus.PENDING,
        )
        db.add(exercise_attempt)
        db.commit()
        return assessment.id, attempt.id, exercise_attempt.id


def _teacher_id(db) -> UUID:
    return db.scalar(
        select(HomeroomTeacherModel.id)
        .join(UserModel, UserModel.id == HomeroomTeacherModel.user_id)
        .where(UserModel.email == "teacher@example.com")
    )


def _create_template_model(name: str, *, active: bool) -> UUID:
    with TestingSessionLocal() as db:
        template = AssessmentTemplateModel(
            name=name,
            version=1,
            is_active=active,
            created_by_teacher_id=_teacher_id(db),
        )
        db.add(template)
        db.commit()
        return template.id


def _create_exercise_model(title: str) -> UUID:
    with TestingSessionLocal() as db:
        exercise = AssessmentExerciseModel(
            type="MULTIPLE_CHOICE",
            title=title,
            is_active=True,
            created_by_teacher_id=_teacher_id(db),
        )
        db.add(exercise)
        db.commit()
        return exercise.id


def _create_template_exercise_model(template_id: UUID, exercise_id: UUID) -> UUID:
    with TestingSessionLocal() as db:
        template_exercise = AssessmentTemplateExerciseModel(
            template_id=template_id,
            exercise_id=exercise_id,
            order_index=1,
            points=2,
            is_required=True,
        )
        db.add(template_exercise)
        db.commit()
        return template_exercise.id


def _reset_args(
    *,
    confirm: bool,
    execute: bool,
    template_name_prefix: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        confirm_reset_demo_data=confirm,
        execute=execute,
        teacher_id=None,
        template_name_prefix=template_name_prefix,
        student_name_prefix=None,
        classroom_name_prefix=None,
    )
