from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime, timezone
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
from app.assessment.infrastructure.models.prompt_model import (
    ExpectedAnswerModel,
    PromptExerciseModel,
)
from app.assessment.infrastructure.models.question_model import (
    MCAnswerOptionModel,
    MCQuestionModel,
    OSAnswerModel,
    OSQuestionModel,
)
from app.assessment.infrastructure.models.response_model import (
    MCResponseModel,
    OSResponseModel,
    SpeakingResponseModel,
    WritingResponseModel,
)
from app.assessment.infrastructure.models.template_model import (
    AssessmentTemplateExerciseModel,
    AssessmentTemplateModel,
)
from app.core.config import Settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.iam.infrastructure.models.refresh_token_model import RefreshTokenModel
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

        student = Student(
            classroom_id=classroom.id,
            code="ST-001",
            age=7,
            gender="BOY",
            is_active=True,
        )
        db.add(student)
        db.flush()

        consent = StudentConsent(
            student_id=student.id,
            status=True,
            consent_date=datetime.now(UTC),
        )
        db.add(consent)
        db.commit()

        # Store IDs for tests
        setup_database.user_id = user.id
        setup_database.teacher_id = teacher.id
        setup_database.classroom_id = classroom.id
        setup_database.student_id = student.id

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
    settings = Settings()
    token = create_access_token(
        subject=str(setup_database.user_id),
        settings=settings,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def teacher_id() -> UUID:
    return setup_database.teacher_id


@pytest.fixture
def classroom_id() -> UUID:
    return setup_database.classroom_id


@pytest.fixture
def student_id() -> UUID:
    return setup_database.student_id


# ─── Tests ─────────────────────────────────────────────────────


def test_create_template(client, teacher_headers):
    response = client.post(
        "/api/v1/assessments/templates",
        headers=teacher_headers,
        json={"name": "Test de Lectoescritura", "description": "Evaluación inicial", "version": 1},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test de Lectoescritura"
    assert data["version"] == 1
    assert data["template_id"] is not None


def test_create_exercise_mc(client, teacher_headers):
    response = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "Letra inicial",
            "instructions": "Selecciona la opción correcta",
            "difficulty_level": 1,
            "mc_question": {
                "question_text": "¿Con qué letra empieza 'casa'?",
                "options": [
                    {"text": "C", "is_correct": True, "order_index": 1},
                    {"text": "P", "is_correct": False, "order_index": 2},
                    {"text": "M", "is_correct": False, "order_index": 3},
                ],
            },
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "MULTIPLE_CHOICE"
    assert data["exercise_id"] is not None


def test_create_exercise_os(client, teacher_headers):
    response = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "ORDER_SYLLABLES",
            "title": "Ordenar sílabas",
            "instructions": "Ordena las sílabas para formar la palabra correcta",
            "difficulty_level": 1,
            "os_question": {
                "question_text": "Ordena las sílabas: sa - ca",
                "correct_word": "casa",
                "syllables_json": ["ca", "sa"],
            },
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "ORDER_SYLLABLES"


def test_create_exercise_prompt(client, teacher_headers):
    response = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "READING_SPEAKING",
            "title": "Lectura en voz alta",
            "instructions": "Lee el texto en voz alta",
            "difficulty_level": 1,
            "prompt_exercise": {
                "prompt_text": "Lee la siguiente frase",
                "text_to_show": "El perro corre por el patio",
                "language_code": "es-PE",
                "expected_text": "El perro corre por el patio",
            },
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "READING_SPEAKING"


def test_attach_exercise_to_template(client, teacher_headers):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates",
        headers=teacher_headers,
        json={"name": "Test", "version": 1},
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "Test",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    )
    exercise_id = ex_resp.json()["exercise_id"]

    response = client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "points": 10, "is_required": True},
    )
    assert response.status_code == 201
    assert response.json()["detail"] == "Exercise attached to template successfully."


def test_create_assessment(client, teacher_headers, classroom_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates",
        headers=teacher_headers,
        json={"name": "Test Assessment", "version": 1},
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC Test",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    )
    exercise_id = ex_resp.json()["exercise_id"]

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "points": 10, "is_required": True},
    )

    response = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={
            "template_id": template_id,
            "classroom_id": str(classroom_id),
            "title": "Evaluación 3A",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Evaluación 3A"
    assert data["status"] == "DRAFT"


def test_start_attempt_creates_exercise_attempts(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates",
        headers=teacher_headers,
        json={"name": "Template", "version": 1},
    )
    template_id = tmpl_resp.json()["template_id"]

    ex1 = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC1",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()["exercise_id"]
    ex2 = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "ORDER_SYLLABLES",
            "title": "OS1",
            "os_question": {
                "question_text": "Ordena",
                "correct_word": "sol",
                "syllables_json": ["sol"],
            },
        },
    ).json()["exercise_id"]

    for ex_id, idx in [(ex1, 1), (ex2, 2)]:
        client.post(
            f"/api/v1/assessments/templates/{template_id}/exercises",
            headers=teacher_headers,
            json={"exercise_id": ex_id, "order_index": idx, "points": 10, "is_required": True},
        )

    asm = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()
    assessment_id = asm["assessment_id"]

    response = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "IN_PROGRESS"
    assert data["attempt_id"] is not None

    detail = client.get(
        f"/api/v1/assessments/attempts/{data['attempt_id']}",
        headers=teacher_headers,
    )
    assert detail.status_code == 200
    assert len(detail.json()["exercise_attempts"]) == 2


def test_submit_mc_response(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "T", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC",
            "mc_question": {
                "question_text": "¿2+2?",
                "options": [
                    {"text": "4", "is_correct": True, "order_index": 1},
                    {"text": "5", "is_correct": False, "order_index": 2},
                ],
            },
        },
    ).json()
    exercise_id = ex_resp["exercise_id"]

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()

    att = client.post(
        f"/api/v1/assessments/{asm['assessment_id']}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()

    # Get the exercise attempt ID
    detail = client.get(
        f"/api/v1/assessments/attempts/{att['attempt_id']}", headers=teacher_headers
    ).json()
    ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]

    # We need to find the correct option ID - we can look it up from the db or
    # we can create the exercise and query the option. For simplicity, let's
    # submit and verify the response works.
    with TestingSessionLocal() as db:
        option = db.query(MCAnswerOptionModel).first()
        option_id = option.id

    response = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/mc-response",
        headers=teacher_headers,
        json={"selected_option_id": str(option_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_correct"] is True


def test_submit_os_response(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "T2", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "ORDER_SYLLABLES",
            "title": "OS",
            "os_question": {
                "question_text": "Ordena",
                "correct_word": "casa",
                "syllables_json": ["ca", "sa"],
            },
        },
    ).json()
    exercise_id = ex_resp["exercise_id"]

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()

    att = client.post(
        f"/api/v1/assessments/{asm['assessment_id']}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()

    detail = client.get(
        f"/api/v1/assessments/attempts/{att['attempt_id']}", headers=teacher_headers
    ).json()
    ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]

    response = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/os-response",
        headers=teacher_headers,
        json={"selected_syllables": ["ca", "sa"], "formed_word": "casa"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_correct"] is True


def test_upload_speaking_response(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "T3", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "READING_SPEAKING",
            "title": "Lectura",
            "prompt_exercise": {
                "text_to_show": "Hola mundo",
                "language_code": "es-PE",
                "expected_text": "Hola mundo",
            },
        },
    ).json()
    exercise_id = ex_resp["exercise_id"]

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()

    att = client.post(
        f"/api/v1/assessments/{asm['assessment_id']}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()

    detail = client.get(
        f"/api/v1/assessments/attempts/{att['attempt_id']}", headers=teacher_headers
    ).json()
    ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]

    response = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio content", "audio/wav")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["audio_blob_path"] is not None


def test_finish_attempt_and_get_result(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "T4", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC",
            "mc_question": {
                "question_text": "¿2+2?",
                "options": [
                    {"text": "4", "is_correct": True, "order_index": 1},
                    {"text": "5", "is_correct": False, "order_index": 2},
                ],
            },
        },
    ).json()
    exercise_id = ex_resp["exercise_id"]

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()

    att = client.post(
        f"/api/v1/assessments/{asm['assessment_id']}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()
    attempt_id = att["attempt_id"]

    detail = client.get(
        f"/api/v1/assessments/attempts/{attempt_id}", headers=teacher_headers
    ).json()
    ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]

    with TestingSessionLocal() as db:
        option = db.query(MCAnswerOptionModel).first()
        option_id = option.id

    client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/mc-response",
        headers=teacher_headers,
        json={"selected_option_id": str(option_id)},
    )

    finish = client.post(
        f"/api/v1/assessments/attempts/{attempt_id}/finish",
        headers=teacher_headers,
    )
    assert finish.status_code == 200
    result_data = finish.json()
    assert result_data["final_score"] is not None
    assert result_data["mc_correct_count"] == 1

    result_get = client.get(
        f"/api/v1/assessments/attempts/{attempt_id}/result",
        headers=teacher_headers,
    )
    assert result_get.status_code == 200
    assert result_get.json()["final_score"] == result_data["final_score"]
