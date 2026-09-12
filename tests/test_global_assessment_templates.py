from __future__ import annotations

import argparse
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import select

from app.assessment.infrastructure.models.exercise_model import AssessmentExerciseModel
from app.assessment.infrastructure.models.template_model import (
    AssessmentTemplateExerciseModel,
    AssessmentTemplateModel,
)
from app.iam.infrastructure.models.user_model import UserModel
from app.school.infrastructure.models.classroom_model import ClassroomModel
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
from conftest import TestingSessionLocal
from scripts.admin import mark_templates_global


def test_list_templates_returns_active_owned_and_global_only(client, teacher_headers):
    teacher_id = _teacher_id("teacher@example.com")
    other_teacher_id = _teacher_id("other@example.com")
    owned = _create_template("Owned active", teacher_id=teacher_id, active=True)
    global_template = _create_template("Global active", teacher_id=None, active=True)
    _create_template("Other private", teacher_id=other_teacher_id, active=True)
    _create_template("Owned inactive", teacher_id=teacher_id, active=False)
    _create_template("Global inactive", teacher_id=None, active=False)

    response = client.get("/api/v1/assessments/templates", headers=teacher_headers)

    assert response.status_code == 200
    ids = {UUID(item["template_id"]) for item in response.json()}
    assert owned in ids
    assert global_template in ids
    assert len(ids) == 2


def test_get_template_by_id_allows_owned_and_global_active(client, teacher_headers):
    teacher_id = _teacher_id("teacher@example.com")
    owned = _create_template("Owned detail", teacher_id=teacher_id, active=True)
    global_template = _create_template("Global detail", teacher_id=None, active=True)

    owned_response = client.get(f"/api/v1/assessments/templates/{owned}", headers=teacher_headers)
    global_response = client.get(f"/api/v1/assessments/templates/{global_template}", headers=teacher_headers)

    assert owned_response.status_code == 200
    assert owned_response.json()["template_id"] == str(owned)
    assert global_response.status_code == 200
    assert global_response.json()["template_id"] == str(global_template)
    assert global_response.json()["created_by_teacher_id"] is None


def test_get_template_by_id_blocks_other_private_and_inactive_global(client, teacher_headers):
    other_teacher_id = _teacher_id("other@example.com")
    other_private = _create_template("Other detail", teacher_id=other_teacher_id, active=True)
    inactive_global = _create_template("Inactive global detail", teacher_id=None, active=False)

    other_response = client.get(f"/api/v1/assessments/templates/{other_private}", headers=teacher_headers)
    inactive_response = client.get(f"/api/v1/assessments/templates/{inactive_global}", headers=teacher_headers)

    assert other_response.status_code == 404
    assert inactive_response.status_code == 404


def test_create_assessment_allows_owned_and_global_active(client, teacher_headers):
    teacher_id = _teacher_id("teacher@example.com")
    classroom_id = _create_classroom(teacher_id)
    owned = _create_template("Owned assessment", teacher_id=teacher_id, active=True)
    global_template = _create_template("Global assessment", teacher_id=None, active=True)

    owned_response = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"classroom_id": str(classroom_id), "template_id": str(owned)},
    )
    global_response = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"classroom_id": str(classroom_id), "template_id": str(global_template)},
    )

    assert owned_response.status_code == 201
    assert owned_response.json()["template_id"] == str(owned)
    assert global_response.status_code == 201
    assert global_response.json()["template_id"] == str(global_template)


def test_create_assessment_blocks_other_private_and_inactive_templates(client, teacher_headers):
    teacher_id = _teacher_id("teacher@example.com")
    other_teacher_id = _teacher_id("other@example.com")
    classroom_id = _create_classroom(teacher_id)
    other_private = _create_template("Other assessment", teacher_id=other_teacher_id, active=True)
    inactive_owned = _create_template("Inactive owned assessment", teacher_id=teacher_id, active=False)
    inactive_global = _create_template("Inactive global assessment", teacher_id=None, active=False)

    for template_id in (other_private, inactive_owned, inactive_global, uuid4()):
        response = client.post(
            "/api/v1/assessments",
            headers=teacher_headers,
            json={"classroom_id": str(classroom_id), "template_id": str(template_id)},
        )
        assert response.status_code == 404


def test_attach_exercise_allows_owned_template_only(client, teacher_headers):
    teacher_id = _teacher_id("teacher@example.com")
    template_id = _create_template("Attach owned", teacher_id=teacher_id, active=True)
    exercise_id = _create_exercise("Attach exercise", teacher_id=teacher_id)

    response = client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": str(exercise_id), "order_index": 1, "points": 2, "is_required": True},
    )

    assert response.status_code == 201


def test_attach_exercise_blocks_global_and_other_private_templates(client, teacher_headers):
    teacher_id = _teacher_id("teacher@example.com")
    other_teacher_id = _teacher_id("other@example.com")
    global_template = _create_template("Attach global", teacher_id=None, active=True)
    other_private = _create_template("Attach other", teacher_id=other_teacher_id, active=True)
    exercise_id = _create_exercise("Attach blocked exercise", teacher_id=teacher_id)

    for template_id in (global_template, other_private):
        response = client.post(
            f"/api/v1/assessments/templates/{template_id}/exercises",
            headers=teacher_headers,
            json={"exercise_id": str(exercise_id), "order_index": 1, "points": 2, "is_required": True},
        )
        assert response.status_code == 404


def test_template_mutations_keep_global_and_other_private_read_only(client, teacher_headers):
    teacher_id = _teacher_id("teacher@example.com")
    other_teacher_id = _teacher_id("other@example.com")
    global_template = _create_template("Mutation global", teacher_id=None, active=True)
    other_private = _create_template("Mutation other", teacher_id=other_teacher_id, active=True)
    exercise_id = _create_exercise("Mutation exercise", teacher_id=teacher_id)
    global_te = _create_template_exercise(global_template, exercise_id)
    other_te = _create_template_exercise(other_private, exercise_id)

    for template_id in (global_template, other_private):
        assert client.patch(
            f"/api/v1/assessments/templates/{template_id}/deactivate",
            headers=teacher_headers,
        ).status_code == 404
        assert client.delete(
            f"/api/v1/assessments/templates/{template_id}",
            headers=teacher_headers,
        ).status_code == 404

    for template_id, template_exercise_id in ((global_template, global_te), (other_private, other_te)):
        response = client.patch(
            f"/api/v1/assessments/templates/{template_id}/exercises/{template_exercise_id}/points",
            headers=teacher_headers,
            json={"points": 1},
        )
        assert response.status_code == 404


def test_mark_templates_global_dry_run_does_not_modify(capsys):
    teacher_id = _teacher_id("teacher@example.com")
    template_id = _create_template("TAMIZAI_DRY_RUN", teacher_id=teacher_id, active=True)
    args = _mark_global_args(template_names=["TAMIZAI_DRY_RUN"], execute=False, confirm=False)

    exit_code = mark_templates_global.run(args, session_factory=TestingSessionLocal)

    assert exit_code == 0
    assert "DRY-RUN" in capsys.readouterr().out
    with TestingSessionLocal() as db:
        template = db.get(AssessmentTemplateModel, template_id)
        assert template.created_by_teacher_id == teacher_id


def test_mark_templates_global_requires_confirmation_for_execute(capsys):
    args = _mark_global_args(template_names=["TAMIZAI_CONFIRM"], execute=True, confirm=False)

    exit_code = mark_templates_global.run(args, session_factory=TestingSessionLocal)

    assert exit_code == 2
    assert "confirm" in capsys.readouterr().out


def test_mark_templates_global_requires_names(capsys):
    args = _mark_global_args(template_names=[], execute=True, confirm=True)

    exit_code = mark_templates_global.run(args, session_factory=TestingSessionLocal)

    assert exit_code == 2
    assert "template-name" in capsys.readouterr().out


def test_mark_templates_global_execute_converts_only_exact_names():
    teacher_id = _teacher_id("teacher@example.com")
    target = _create_template("TAMIZAI_6A", teacher_id=teacher_id, active=True)
    similarly_named = _create_template("TAMIZAI_6A_COPY", teacher_id=teacher_id, active=True)
    unlisted = _create_template("TAMIZAI_9A", teacher_id=teacher_id, active=True)
    args = _mark_global_args(template_names=["TAMIZAI_6A"], execute=True, confirm=True)

    exit_code = mark_templates_global.run(args, session_factory=TestingSessionLocal)

    assert exit_code == 0
    with TestingSessionLocal() as db:
        assert db.get(AssessmentTemplateModel, target).created_by_teacher_id is None
        assert db.get(AssessmentTemplateModel, similarly_named).created_by_teacher_id == teacher_id
        assert db.get(AssessmentTemplateModel, unlisted).created_by_teacher_id == teacher_id


def _teacher_id(email: str) -> UUID:
    with TestingSessionLocal() as db:
        return db.scalar(
            select(HomeroomTeacherModel.id)
            .join(UserModel, UserModel.id == HomeroomTeacherModel.user_id)
            .where(UserModel.email == email)
        )


def _create_template(name: str, *, teacher_id: UUID | None, active: bool) -> UUID:
    with TestingSessionLocal() as db:
        template = AssessmentTemplateModel(
            name=name,
            version=1,
            is_active=active,
            created_by_teacher_id=teacher_id,
        )
        db.add(template)
        db.commit()
        return template.id


def _create_exercise(title: str, *, teacher_id: UUID | None) -> UUID:
    with TestingSessionLocal() as db:
        exercise = AssessmentExerciseModel(
            type="MULTIPLE_CHOICE",
            title=title,
            is_active=True,
            created_by_teacher_id=teacher_id,
        )
        db.add(exercise)
        db.commit()
        return exercise.id


def _create_template_exercise(template_id: UUID, exercise_id: UUID) -> UUID:
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


def _create_classroom(teacher_id: UUID) -> UUID:
    with TestingSessionLocal() as db:
        classroom = ClassroomModel(
            homeroom_teacher_id=teacher_id,
            name=f"Global Templates {uuid4()}",
            grade_level="primero",
            section="A",
            school_year=date(2026, 1, 1),
            is_active=True,
        )
        db.add(classroom)
        db.commit()
        return classroom.id


def _mark_global_args(
    *,
    template_names: list[str],
    execute: bool,
    confirm: bool,
) -> argparse.Namespace:
    return argparse.Namespace(
        template_name=template_names,
        execute=execute,
        confirm_mark_global=confirm,
    )
