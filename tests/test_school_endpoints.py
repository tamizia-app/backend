from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.assessment.infrastructure.models.assessment_model import AssessmentModel
from app.assessment.infrastructure.models.attempt_model import (
    AssessmentAttemptModel,
    ExerciseAttemptModel,
)
from app.assessment.infrastructure.models.exercise_model import AssessmentExerciseModel
from app.assessment.infrastructure.models.metrics_model import AssessmentResultModel
from app.assessment.infrastructure.models.template_model import (
    AssessmentTemplateExerciseModel,
    AssessmentTemplateModel,
)
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.iam.infrastructure.models.user_model import UserModel
from app.main import app
from app.school.infrastructure.models.classroom_model import ClassroomModel
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
from app.school.infrastructure.models.student_model import Student, StudentConsent
from app.shared.base import Base

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        user = UserModel(
            name="Teacher",
            lastname="One",
            email="teacher@example.com",
            password_hash=hash_password("secret123"),
            is_active=True,
        )
        db.add(user)
        db.flush()

        teacher = HomeroomTeacherModel(
            user_id=user.id,
            institute_name="Colegio Demo",
            phone="999999999",
        )
        db.add(teacher)
        db.flush()

        classroom = ClassroomModel(
            homeroom_teacher_id=teacher.id,
            name="3A",
            grade_level="primero",
            section="A",
            school_year=date(2026, 1, 1),
            is_active=True,
        )
        db.add(classroom)
        db.flush()

        student1 = Student(
            classroom_id=classroom.id,
            code="ST-001",
            age=7,
            gender="BOY",
            is_active=True,
        )
        db.add(student1)
        db.flush()

        student2 = Student(
            classroom_id=classroom.id,
            code="ST-002",
            age=8,
            gender="GIRL",
            is_active=True,
        )
        db.add(student2)
        db.flush()

        consent1 = StudentConsent(
            student_id=student1.id,
            status=True,
            consent_date=datetime.now(UTC),
        )
        db.add(consent1)
        consent2 = StudentConsent(
            student_id=student2.id,
            status=True,
            consent_date=datetime.now(UTC),
        )
        db.add(consent2)

        # Second teacher (for isolation)
        other_user = UserModel(
            name="Other", lastname="Teacher",
            email="other@example.com",
            password_hash=hash_password("secret123"),
            is_active=True,
        )
        db.add(other_user)
        db.flush()
        other_teacher = HomeroomTeacherModel(
            user_id=other_user.id, institute_name="Other", phone="888888888",
        )
        db.add(other_teacher)
        db.flush()

        # Template + Assessment for dashboard count
        tmpl = AssessmentTemplateModel(
            name="Template 1", version=1,
            created_by_teacher_id=teacher.id,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(tmpl)
        db.flush()

        asm = AssessmentModel(
            template_id=tmpl.id,
            classroom_id=classroom.id,
            homeroom_teacher_id=teacher.id,
            title="Assessment 1",
            status="ACTIVE",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(asm)
        db.flush()

        att = AssessmentAttemptModel(
            assessment_id=asm.id,
            student_id=student1.id,
            status="IN_PROGRESS",
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(att)
        db.commit()

        setup_database.user_id = user.id
        setup_database.teacher_id = teacher.id
        setup_database.other_user_id = other_user.id
        setup_database.classroom_id = classroom.id
        setup_database.student1_id = student1.id
        setup_database.student2_id = student2.id

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def teacher_headers(client: TestClient) -> dict[str, str]:
    from app.core.config import Settings
    settings = Settings()
    token = create_access_token(subject=str(setup_database.user_id), settings=settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_teacher_headers(client: TestClient) -> dict[str, str]:
    from app.core.config import Settings
    settings = Settings()
    token = create_access_token(subject=str(setup_database.other_user_id), settings=settings)
    return {"Authorization": f"Bearer {token}"}


# ─── GET /students ─────────────────────────────────────────────


def test_list_all_students(client, teacher_headers):
    resp = client.get("/api/v1/students", headers=teacher_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["limit"] == 20
    assert data["offset"] == 0
    for item in data["items"]:
        assert "student_id" in item
        assert "classroom" in item
        assert item["classroom"]["name"] == "3A"


def test_list_all_students_pagination(client, teacher_headers):
    resp = client.get("/api/v1/students?limit=1&offset=0", headers=teacher_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["total"] == 2
    assert data["limit"] == 1
    assert data["offset"] == 0

    resp2 = client.get("/api/v1/students?limit=1&offset=1", headers=teacher_headers)
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 1


def test_list_all_students_search(client, teacher_headers):
    resp = client.get("/api/v1/students?q=ST-001", headers=teacher_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["code"] == "ST-001"


def test_list_all_students_filter_by_classroom(client, teacher_headers, monkeypatch):
    resp = client.get(f"/api/v1/students?classroom_id={setup_database.classroom_id}", headers=teacher_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


def test_list_all_students_filter_inactive(client, teacher_headers):
    resp = client.get("/api/v1/students?is_active=false", headers=teacher_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0

    resp2 = client.get("/api/v1/students?is_active=true", headers=teacher_headers)
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 2


def test_list_all_students_teacher_isolation(client, teacher_headers, other_teacher_headers):
    resp = client.get("/api/v1/students", headers=other_teacher_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_all_students_unauthorized(client):
    resp = client.get("/api/v1/students")
    assert resp.status_code == 401


# ─── GET /dashboard/summary ────────────────────────────────────


def test_dashboard_summary_returns_counts(client, teacher_headers):
    resp = client.get("/api/v1/dashboard/summary", headers=teacher_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_students"] == 2
    assert data["total_classrooms"] == 1
    assert data["total_templates"] == 1
    assert data["total_assessments"] == 1
    assert data["in_progress_attempts"] == 1
    assert data["completed_attempts"] == 0


def test_dashboard_summary_other_teacher_empty(client, teacher_headers, other_teacher_headers):
    resp = client.get("/api/v1/dashboard/summary", headers=other_teacher_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_students"] == 0
    assert data["total_classrooms"] == 0
    assert data["total_templates"] == 0
    assert data["total_assessments"] == 0
    assert data["completed_attempts"] == 0
    assert data["in_progress_attempts"] == 0


def test_dashboard_summary_unauthorized(client):
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 401


# ─── GET /students/{student_id} (existing) ─────────────────────


def test_get_student_by_id(client, teacher_headers):
    resp = client.get(f"/api/v1/students/{setup_database.student1_id}", headers=teacher_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert str(data["student_id"]) == str(setup_database.student1_id)
    assert data["code"] == "ST-001"


def test_get_student_not_found(client, teacher_headers):
    fake_id = uuid.uuid4()
    resp = client.get(f"/api/v1/students/{fake_id}", headers=teacher_headers)
    assert resp.status_code == 404
