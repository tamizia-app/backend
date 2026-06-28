from __future__ import annotations

import json
import uuid
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


def test_upload_speaking_response(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {
            "status": "completed",
            "recognized_text": "hola mundo",
            "stt_recognized_text": "hola mundo",
            "assessment_recognized_text": "hola mundo",
            "pronunciation_score": 85.0,
            "accuracy_score": 80.0,
            "fluency_score": 90.0,
            "completeness_score": 95.0,
            "prosody_score": None,
            "comparison": None,
            "review": {},
            "error_message": None,
            "duration_ms": 1500,
            "raw_result_json": {"NBest": [{"PronScore": 85}]},
            "stt": {"text": "hola mundo", "segments": [], "language": "es", "duration_ms": 1500},
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

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
    assert data["free_transcription_text"] == "hola mundo"
    assert data["assessment_recognized_text"] == "hola mundo"
    assert data["pronunciation_score"] == 85.0
    assert data["accuracy_score"] == 80.0
    assert data["fluency_score"] == 90.0
    assert data["completeness_score"] == 95.0
    assert data["prosody_score"] is None
    assert data["evaluation_status"] == "completed"


def _create_speaking_setup(client, teacher_headers, classroom_id, student_id, exercise_type="READING_SPEAKING", expected_text="Hola mundo"):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "T", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    body = {
        "type": exercise_type,
        "title": "Test",
        "instructions": "Read aloud",
        "difficulty_level": 1,
    }
    if exercise_type in ("READING_SPEAKING", "LISTENING_SPEAKING"):
        body["prompt_exercise"] = {
            "prompt_text": "Read this",
            "text_to_show": "Hola mundo",
            "language_code": "es-PE",
            "expected_text": expected_text,
        }
    elif exercise_type == "MULTIPLE_CHOICE":
        body["mc_question"] = {
            "question_text": "Q?",
            "options": [{"text": "A", "is_correct": True, "order_index": 1}],
        }

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json=body,
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
    return detail["exercise_attempts"][0]["exercise_attempt_id"]


def test_upload_speaking_response_saves_metrics(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {
            "status": "completed",
            "recognized_text": "hola mundo",
            "stt_recognized_text": "hola mundo",
            "assessment_recognized_text": "hola mundo",
            "pronunciation_score": 85.0,
            "accuracy_score": 80.0,
            "fluency_score": 90.0,
            "completeness_score": 95.0,
            "prosody_score": None,
            "comparison": None,
            "review": {},
            "error_message": None,
            "duration_ms": 1500,
            "raw_result_json": {"NBest": [{"PronScore": 85}]},
            "stt": {"text": "hola mundo", "segments": [{"id": 0, "text": "hola mundo"}], "language": "es", "duration_ms": 1500},
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    ea_id = _create_speaking_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio content", "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluation_status"] == "completed"

    with TestingSessionLocal() as db:
        from app.assessment.infrastructure.models.metrics_model import SpeakingMetricsModel
        metrics = db.query(SpeakingMetricsModel).first()
        assert metrics is not None
        assert metrics.pronunciation_score == 85.0
        assert metrics.accuracy_score == 80.0
        assert metrics.fluency_score == 90.0
        assert metrics.completeness_score == 95.0
        assert metrics.prosody_score is None
        assert metrics.raw_speech_result_json["NBest"][0]["PronScore"] == 85
        assert metrics.raw_transcription_result_json["text"] == "hola mundo"
        assert metrics.raw_transcription_result_json["segments"][0]["text"] == "hola mundo"


def test_upload_speaking_response_whisper_fails_azure_works(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {
            "status": "partial",
            "recognized_text": None,
            "stt_recognized_text": None,
            "assessment_recognized_text": "hola mundo",
            "pronunciation_score": 85.0,
            "accuracy_score": 80.0,
            "fluency_score": 90.0,
            "completeness_score": 95.0,
            "prosody_score": None,
            "comparison": None,
            "review": {},
            "error_message": "One or more assessment providers failed.",
            "duration_ms": 1500,
            "raw_result_json": {"NBest": [{"PronScore": 85}]},
            "stt": {"status": "failed", "error": {"code": "STT_PROVIDER_FAILED", "message": "Whisper failed"}},
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    ea_id = _create_speaking_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio content", "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluation_status"] == "partial"
    assert data["free_transcription_text"] is None
    assert data["assessment_recognized_text"] == "hola mundo"
    assert data["pronunciation_score"] == 85.0


def test_upload_speaking_response_azure_fails_whisper_works(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {
            "status": "partial",
            "recognized_text": "hola mundo",
            "stt_recognized_text": "hola mundo",
            "assessment_recognized_text": None,
            "pronunciation_score": None,
            "accuracy_score": None,
            "fluency_score": None,
            "completeness_score": None,
            "prosody_score": None,
            "comparison": {"source": "expected_text_vs_faster_whisper"},
            "review": {"requires_review": True},
            "error_message": "One or more assessment providers failed.",
            "duration_ms": 1500,
            "raw_result_json": {},
            "stt": {"text": "hola mundo", "segments": [], "language": "es", "duration_ms": 1500},
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    ea_id = _create_speaking_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio content", "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluation_status"] == "partial"
    assert data["free_transcription_text"] == "hola mundo"
    assert data["assessment_recognized_text"] is None
    assert data["pronunciation_score"] is None
    assert data["comparison"] is not None
    assert data["review"] is not None


def test_upload_speaking_response_both_fail(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {
            "status": "failed",
            "recognized_text": None,
            "stt_recognized_text": None,
            "assessment_recognized_text": None,
            "pronunciation_score": None,
            "accuracy_score": None,
            "fluency_score": None,
            "completeness_score": None,
            "prosody_score": None,
            "comparison": None,
            "review": {},
            "error_message": "One or more assessment providers failed.",
            "duration_ms": 1500,
            "raw_result_json": {},
            "stt": {"status": "failed", "error": {"code": "STT_PROVIDER_FAILED"}},
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    ea_id = _create_speaking_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio content", "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluation_status"] == "failed"
    assert data["audio_blob_path"] is not None
    assert data["free_transcription_text"] is None
    assert data["assessment_recognized_text"] is None
    assert data["pronunciation_score"] is None


def test_upload_speaking_response_rejects_wrong_exercise_type(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {"status": "completed", "recognized_text": ""}

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    ea_id = _create_speaking_setup(client, teacher_headers, classroom_id, student_id, exercise_type="MULTIPLE_CHOICE")

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio content", "audio/wav")},
    )
    assert resp.status_code == 400
    assert "speaking" in resp.json()["detail"].lower()


def test_upload_speaking_response_missing_expected_text(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {"status": "completed", "recognized_text": ""}

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    ea_id = _create_speaking_setup(client, teacher_headers, classroom_id, student_id, expected_text="")

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio content", "audio/wav")},
    )
    assert resp.status_code == 400
    assert "expected text" in resp.json()["detail"].lower()


def test_upload_speaking_response_uses_language_code_from_prompt(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    captured_locales = []

    async def mock_execute(self, command):
        captured_locales.append(command.assessment_locale)
        return {
            "status": "completed",
            "recognized_text": "hola",
            "assessment_recognized_text": "hola",
            "pronunciation_score": 90.0,
            "accuracy_score": 90.0,
            "fluency_score": 90.0,
            "completeness_score": 90.0,
            "prosody_score": None,
            "raw_result_json": {},
            "stt": {"text": "hola", "segments": [], "language": "es"},
            "duration_ms": 1000,
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TLang", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "READING_SPEAKING",
            "title": "Lang Test",
            "prompt_exercise": {
                "text_to_show": "Hola",
                "language_code": "es-ES",
                "expected_text": "Hola",
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

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio content", "audio/wav")},
    )
    assert resp.status_code == 200
    assert captured_locales == ["es-ES"]


def test_upload_speaking_response_prosody_none_does_not_fail(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {
            "status": "completed",
            "recognized_text": "hola",
            "assessment_recognized_text": "hola",
            "pronunciation_score": 85.0,
            "accuracy_score": 80.0,
            "fluency_score": 90.0,
            "completeness_score": 95.0,
            "prosody_score": None,
            "raw_result_json": {},
            "stt": {"text": "hola", "segments": [], "language": "es"},
            "duration_ms": 1000,
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    ea_id = _create_speaking_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio content", "audio/wav")},
    )
    assert resp.status_code == 200
    assert resp.json()["prosody_score"] is None


def test_upload_speaking_response_update_existing(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    call_count = 0

    async def mock_execute(self, command):
        nonlocal call_count
        call_count += 1
        return {
            "status": "completed",
            "recognized_text": f"version {call_count}",
            "assessment_recognized_text": f"version {call_count}",
            "pronunciation_score": 85.0,
            "accuracy_score": 80.0,
            "fluency_score": 90.0,
            "completeness_score": 95.0,
            "prosody_score": None,
            "raw_result_json": {},
            "stt": {"text": f"version {call_count}", "segments": [], "language": "es"},
            "duration_ms": 1500,
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    ea_id = _create_speaking_setup(client, teacher_headers, classroom_id, student_id)

    resp1 = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio content", "audio/wav")},
    )
    assert resp1.status_code == 200
    assert resp1.json()["free_transcription_text"] == "version 1"

    resp2 = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test2.wav", b"more fake audio", "audio/wav")},
    )
    assert resp2.status_code == 200
    assert resp2.json()["free_transcription_text"] == "version 2"

    with TestingSessionLocal() as db:
        from app.assessment.infrastructure.models.response_model import SpeakingResponseModel
        records = db.query(SpeakingResponseModel).all()
        assert len(records) == 1
        assert records[0].free_transcription_text == "version 2"


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


def test_speaking_response_model_new_fields():
    """free_transcription_text and assessment_recognized_text can be stored and retrieved."""
    from app.assessment.infrastructure.models.response_model import SpeakingResponseModel
    from app.shared.base import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    response = SpeakingResponseModel(
        id=uuid.uuid4(),
        exercise_attempt_id=uuid.uuid4(),
        audio_blob_path="test.wav",
        original_filename="test.wav",
        content_type="audio/wav",
        duration_ms=1000,
        recognized_text="whisper legacy",
        free_transcription_text="whisper free text",
        assessment_recognized_text="azure aligned text",
    )
    session.add(response)
    session.flush()
    session.refresh(response)
    assert response.free_transcription_text == "whisper free text"
    assert response.assessment_recognized_text == "azure aligned text"
    assert response.recognized_text == "whisper legacy"
    session.close()


def test_speaking_metrics_model_new_fields():
    """raw_transcription_result_json can be stored and retrieved."""
    from app.assessment.infrastructure.models.metrics_model import SpeakingMetricsModel
    from app.shared.base import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    metrics = SpeakingMetricsModel(
        id=uuid.uuid4(),
        speaking_response_id=uuid.uuid4(),
        raw_transcription_result_json={"text": "whisper result", "segments": []},
        raw_speech_result_json={"NBest": [{"PronScore": 90}]},
    )
    session.add(metrics)
    session.flush()
    session.refresh(metrics)
    assert metrics.raw_transcription_result_json["text"] == "whisper result"
    assert metrics.raw_speech_result_json["NBest"][0]["PronScore"] == 90
    session.close()


def test_create_attempt_returns_exercise_attempts(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TEA", "version": 1}
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

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": ex1, "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()

    response = client.post(
        f"/api/v1/assessments/{asm['assessment_id']}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    )
    assert response.status_code == 201
    data = response.json()
    assert "exercise_attempts" in data
    assert len(data["exercise_attempts"]) == 1
    ea = data["exercise_attempts"][0]
    assert "exercise_attempt_id" in ea
    assert ea["template_exercise_id"] is not None
    assert ea["status"] == "PENDING"


def test_get_attempt_detail_includes_exercise_data(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TED", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC Detail",
            "instructions": "Pick one",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()
    exercise_id = ex_resp["exercise_id"]

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 2, "points": 5, "is_required": False},
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
        f"/api/v1/assessments/attempts/{att['attempt_id']}",
        headers=teacher_headers,
    )
    assert detail.status_code == 200
    items = detail.json()["exercise_attempts"]
    assert len(items) == 1
    item = items[0]
    assert "exercise" in item
    ex = item["exercise"]
    assert ex["exercise_id"] == exercise_id
    assert ex["type"] == "MULTIPLE_CHOICE"
    assert ex["title"] == "MC Detail"
    assert ex["instructions"] == "Pick one"
    assert ex["order_index"] == 2
    assert ex["points"] == 5
    assert ex["is_required"] == False


def test_list_attempts_by_assessment(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TLA", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
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
    assessment_id = asm["assessment_id"]

    client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    )

    resp = client.get(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers=teacher_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    item = data["items"][0]
    assert item["status"] == "IN_PROGRESS"
    assert item["final_score"] is None


def test_list_attempts_filter_by_student(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TLF", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": ex_resp["exercise_id"], "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()
    assessment_id = asm["assessment_id"]

    client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    )

    resp = client.get(
        f"/api/v1/assessments/{assessment_id}/attempts?student_id={student_id}",
        headers=teacher_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1

    fake_id = uuid.uuid4()
    resp2 = client.get(
        f"/api/v1/assessments/{assessment_id}/attempts?student_id={fake_id}",
        headers=teacher_headers,
    )
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 0


def test_get_speaking_response_not_found(client, teacher_headers, classroom_id, student_id):
    fake_id = uuid.uuid4()
    resp = client.get(
        f"/api/v1/assessments/exercise-attempts/{fake_id}/speaking-response",
        headers=teacher_headers,
    )
    assert resp.status_code == 404


def test_get_speaking_response_returns_saved_data(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TSR", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    from app.assessment.infrastructure.models.prompt_model import ExpectedAnswerModel, PromptExerciseModel

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "READING_SPEAKING",
            "title": "Speaking",
            "instructions": "Read aloud",
            "prompt_exercise": {
                "prompt_text": "Read",
                "text_to_show": "El gato",
                "expected_text": "El gato",
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
    ea_id = att["exercise_attempts"][0]["exercise_attempt_id"]

    from app.assessment.infrastructure.models.response_model import SpeakingResponseModel

    with TestingSessionLocal() as db:
        from app.assessment.infrastructure.models.metrics_model import SpeakingMetricsModel
        sr = SpeakingResponseModel(
            id=uuid.uuid4(),
            exercise_attempt_id=uuid.UUID(ea_id),
            audio_blob_path="audio/test.wav",
            original_filename="test.wav",
            content_type="audio/wav",
            duration_ms=3000,
            free_transcription_text="el gato",
            assessment_recognized_text="El gato.",
            recognized_text="el gato",
        )
        db.add(sr)
        db.flush()
        sm = SpeakingMetricsModel(
            id=uuid.uuid4(),
            speaking_response_id=sr.id,
            pronunciation_score=95.0,
            accuracy_score=90.0,
            fluency_score=85.0,
            completeness_score=88.0,
            prosody_score=None,
            raw_speech_result_json={"comparison": {"lexical_match_percentage": 100}, "review": {"required": False}},
            raw_transcription_result_json={"text": "el gato"},
        )
        db.add(sm)
        db.commit()

    resp = client.get(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/speaking-response",
        headers=teacher_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["response_id"] is not None
    assert data["exercise_attempt_id"] == ea_id
    assert data["audio_blob_path"] == "audio/test.wav"
    assert data["pronunciation_score"] == 95.0
    assert data["accuracy_score"] == 90.0
    assert data["fluency_score"] == 85.0
    assert data["completeness_score"] == 88.0
    assert data["prosody_score"] is None
    assert data["evaluation_status"] == "completed"
    assert data["comparison"] is not None
    assert data["review"] is not None
    assert data["review"]["required"] == False


def test_get_attempt_detail_returns_mc_question_without_is_correct(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TMCQ", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC Question Test",
            "instructions": "Pick",
            "mc_question": {
                "question_text": "¿Cuál es correcta?",
                "options": [
                    {"text": "Opción A", "is_correct": True, "order_index": 1},
                    {"text": "Opción B", "is_correct": False, "order_index": 2},
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

    detail = client.get(
        f"/api/v1/assessments/attempts/{att['attempt_id']}",
        headers=teacher_headers,
    )
    assert detail.status_code == 200
    items = detail.json()["exercise_attempts"]
    assert len(items) == 1
    ex = items[0]["exercise"]
    assert ex["type"] == "MULTIPLE_CHOICE"
    assert "mc_question" in ex
    mc_q = ex["mc_question"]
    assert mc_q["question_text"] == "¿Cuál es correcta?"
    assert "options" in mc_q
    assert len(mc_q["options"]) == 2
    for opt in mc_q["options"]:
        assert "option_id" in opt
        assert "text" in opt
        assert "order_index" in opt
        assert "is_correct" not in opt, "is_correct must NOT be exposed to students"


def test_get_attempt_detail_returns_os_question_without_correct_word(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TOSQ", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "ORDER_SYLLABLES",
            "title": "OS Question Test",
            "instructions": "Ordena",
            "os_question": {
                "question_text": "Ordena las sílabas",
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
        f"/api/v1/assessments/attempts/{att['attempt_id']}",
        headers=teacher_headers,
    )
    assert detail.status_code == 200
    items = detail.json()["exercise_attempts"]
    assert len(items) == 1
    ex = items[0]["exercise"]
    assert ex["type"] == "ORDER_SYLLABLES"
    assert "os_question" in ex
    os_q = ex["os_question"]
    assert os_q["question_text"] == "Ordena las sílabas"
    assert os_q["syllables_json"] == ["ca", "sa"]
    assert "correct_word" not in os_q, "correct_word must NOT be exposed to students"


def test_submit_mc_incorrect(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TMCI", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC Incorrect",
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

    detail = client.get(
        f"/api/v1/assessments/attempts/{att['attempt_id']}", headers=teacher_headers
    ).json()
    ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]

    # Get wrong option ID
    with TestingSessionLocal() as db:
        wrong_option = db.query(MCAnswerOptionModel).filter(MCAnswerOptionModel.is_correct == False).first()
        wrong_option_id = wrong_option.id

    response = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/mc-response",
        headers=teacher_headers,
        json={"selected_option_id": str(wrong_option_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_correct"] is False


def test_submit_os_incorrect(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TOSI", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "ORDER_SYLLABLES",
            "title": "OS Incorrect",
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
        json={"selected_syllables": ["sa", "ca"], "formed_word": "saca"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_correct"] is False


def test_mc_response_sets_answered_and_submitted_at(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TMCSA", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC Status",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": ex_resp["exercise_id"], "order_index": 1, "points": 10, "is_required": True},
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

    with TestingSessionLocal() as db:
        option = db.query(MCAnswerOptionModel).first()
        option_id = option.id

    client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/mc-response",
        headers=teacher_headers,
        json={"selected_option_id": str(option_id)},
    )

    # Verify status updated in detail
    detail2 = client.get(
        f"/api/v1/assessments/attempts/{att['attempt_id']}", headers=teacher_headers
    ).json()
    ea = detail2["exercise_attempts"][0]
    assert ea["status"] == "ANSWERED"
    assert ea["submitted_at"] is not None


def test_os_response_sets_answered_and_submitted_at(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TOSSA", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "ORDER_SYLLABLES",
            "title": "OS Status",
            "os_question": {
                "question_text": "Ordena",
                "correct_word": "sol",
                "syllables_json": ["sol"],
            },
        },
    ).json()

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": ex_resp["exercise_id"], "order_index": 1, "points": 10, "is_required": True},
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

    client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/os-response",
        headers=teacher_headers,
        json={"selected_syllables": ["sol"], "formed_word": "sol"},
    )

    detail2 = client.get(
        f"/api/v1/assessments/attempts/{att['attempt_id']}", headers=teacher_headers
    ).json()
    ea = detail2["exercise_attempts"][0]
    assert ea["status"] == "ANSWERED"
    assert ea["submitted_at"] is not None


def test_mc_reattempt_overwrites_previous(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TMR", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC Reattempt",
            "mc_question": {
                "question_text": "¿2+2?",
                "options": [
                    {"text": "4", "is_correct": True, "order_index": 1},
                    {"text": "5", "is_correct": False, "order_index": 2},
                ],
            },
        },
    ).json()

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": ex_resp["exercise_id"], "order_index": 1, "points": 10, "is_required": True},
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

    with TestingSessionLocal() as db:
        options = db.query(MCAnswerOptionModel).order_by(MCAnswerOptionModel.order_index).all()
        correct_id = options[0].id
        wrong_id = options[1].id

    # Submit correct first
    resp1 = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/mc-response",
        headers=teacher_headers,
        json={"selected_option_id": str(correct_id)},
    )
    assert resp1.json()["is_correct"] is True

    # Submit incorrect (overwrite)
    resp2 = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/mc-response",
        headers=teacher_headers,
        json={"selected_option_id": str(wrong_id)},
    )
    assert resp2.json()["is_correct"] is False

    # Verify only one response exists
    with TestingSessionLocal() as db:
        responses = db.query(MCResponseModel).filter(MCResponseModel.exercise_attempt_id == uuid.UUID(ea_id)).all()
        assert len(responses) == 1
        assert responses[0].selected_option_id == wrong_id
        assert responses[0].is_correct == False


def test_os_reattempt_overwrites_previous(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TOR", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "ORDER_SYLLABLES",
            "title": "OS Reattempt",
            "os_question": {
                "question_text": "Ordena",
                "correct_word": "casa",
                "syllables_json": ["ca", "sa"],
            },
        },
    ).json()

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": ex_resp["exercise_id"], "order_index": 1, "points": 10, "is_required": True},
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

    # Submit correct first
    resp1 = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/os-response",
        headers=teacher_headers,
        json={"selected_syllables": ["ca", "sa"], "formed_word": "casa"},
    )
    assert resp1.json()["is_correct"] is True

    # Submit incorrect (overwrite)
    resp2 = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/os-response",
        headers=teacher_headers,
        json={"selected_syllables": ["sa", "ca"], "formed_word": "saca"},
    )
    assert resp2.json()["is_correct"] is False

    # Verify only one response exists
    with TestingSessionLocal() as db:
        responses = db.query(OSResponseModel).filter(OSResponseModel.exercise_attempt_id == uuid.UUID(ea_id)).all()
        assert len(responses) == 1
        assert responses[0].formed_word == "saca"
        assert responses[0].is_correct == False


def test_finish_mixed_assessment_mc_os_speaking(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {
            "status": "completed",
            "recognized_text": "el gato esta en la casa",
            "stt_recognized_text": "el gato esta en la casa",
            "assessment_recognized_text": "El gato está en la casa.",
            "pronunciation_score": 90.0,
            "accuracy_score": 85.0,
            "fluency_score": 88.0,
            "completeness_score": 95.0,
            "prosody_score": None,
            "comparison": None,
            "review": {},
            "error_message": None,
            "duration_ms": 2000,
            "raw_result_json": {"NBest": [{"PronScore": 90}]},
            "stt": {"text": "el gato esta en la casa", "segments": [], "language": "es", "duration_ms": 2000},
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TMIX", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    mc_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC Mix",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()
    os_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "ORDER_SYLLABLES",
            "title": "OS Mix",
            "os_question": {
                "question_text": "Ordena",
                "correct_word": "sol",
                "syllables_json": ["sol"],
            },
        },
    ).json()
    sp_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "READING_SPEAKING",
            "title": "Speaking Mix",
            "prompt_exercise": {
                "text_to_show": "El gato",
                "language_code": "es-PE",
                "expected_text": "El gato está en la casa.",
            },
        },
    ).json()
    sp_exercise_id = sp_resp["exercise_id"]

    for ex_id, idx in [(mc_resp["exercise_id"], 1), (os_resp["exercise_id"], 2), (sp_exercise_id, 3)]:
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

    att = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()
    attempt_id = att["attempt_id"]

    detail = client.get(
        f"/api/v1/assessments/attempts/{attempt_id}", headers=teacher_headers
    ).json()

    # Submit MC (correct)
    mc_ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]
    with TestingSessionLocal() as db:
        option = db.query(MCAnswerOptionModel).first()
        option_id = option.id
    client.post(
        f"/api/v1/assessments/exercise-attempts/{mc_ea_id}/mc-response",
        headers=teacher_headers,
        json={"selected_option_id": str(option_id)},
    )

    # Submit OS (correct)
    os_ea_id = detail["exercise_attempts"][1]["exercise_attempt_id"]
    client.post(
        f"/api/v1/assessments/exercise-attempts/{os_ea_id}/os-response",
        headers=teacher_headers,
        json={"selected_syllables": ["sol"], "formed_word": "sol"},
    )

    # Submit Speaking
    sp_ea_id = detail["exercise_attempts"][2]["exercise_attempt_id"]
    client.post(
        f"/api/v1/assessments/exercise-attempts/{sp_ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio", "audio/wav")},
    )

    # Finish
    finish = client.post(
        f"/api/v1/assessments/attempts/{attempt_id}/finish",
        headers=teacher_headers,
    )
    data = finish.json()
    assert data["final_score"] is not None
    assert data["intervention_level"] in ("LOW", "MEDIUM", "HIGH")
    # MC correct = 100, OS correct = 100, Speaking = avg(90,85,95) = 90 -> avg(100,100,90) ≈ 96.67
    assert 90 <= data["final_score"] <= 100


def test_finish_with_pending_required_exercise_returns_404(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TPEND", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC Pend",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": ex_resp["exercise_id"], "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()
    assessment_id = asm["assessment_id"]

    att = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()

    finish = client.post(
        f"/api/v1/assessments/attempts/{att['attempt_id']}/finish",
        headers=teacher_headers,
    )
    assert finish.status_code == 404


def test_get_result_mixed_assessment_returns_correct_computed_fields(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {
            "status": "completed",
            "recognized_text": "el gato",
            "stt_recognized_text": "el gato",
            "assessment_recognized_text": "El gato.",
            "pronunciation_score": 100.0,
            "accuracy_score": 100.0,
            "fluency_score": 100.0,
            "completeness_score": 100.0,
            "prosody_score": None,
            "comparison": {"lexical_match_percentage": 98.0},
            "review": {},
            "error_message": None,
            "duration_ms": 2000,
            "raw_result_json": {"NBest": [{"PronScore": 100}]},
            "stt": {"text": "el gato", "segments": [], "language": "es", "duration_ms": 2000},
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TGR", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    mc = client.post(
        "/api/v1/assessments/exercises", headers=teacher_headers, json={
            "type": "MULTIPLE_CHOICE", "title": "MC",
            "mc_question": {"question_text": "Q?", "options": [{"text": "A", "is_correct": True, "order_index": 1}]},
        }).json()
    os = client.post(
        "/api/v1/assessments/exercises", headers=teacher_headers, json={
            "type": "ORDER_SYLLABLES", "title": "OS",
            "os_question": {"question_text": "Ordena", "correct_word": "sol", "syllables_json": ["sol"]},
        }).json()
    sp = client.post(
        "/api/v1/assessments/exercises", headers=teacher_headers, json={
            "type": "READING_SPEAKING", "title": "Speaking",
            "prompt_exercise": {"text_to_show": "El gato", "language_code": "es-PE", "expected_text": "El gato"},
        }).json()

    for ex_id, idx in [(mc["exercise_id"], 1), (os["exercise_id"], 2), (sp["exercise_id"], 3)]:
        client.post(
            f"/api/v1/assessments/templates/{template_id}/exercises",
            headers=teacher_headers,
            json={"exercise_id": ex_id, "order_index": idx, "points": 10, "is_required": True},
        )

    asm = client.post(
        "/api/v1/assessments", headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()
    assessment_id = asm["assessment_id"]

    att = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts", headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()
    attempt_id = att["attempt_id"]

    detail = client.get(
        f"/api/v1/assessments/attempts/{attempt_id}", headers=teacher_headers
    ).json()

    # Submit MC correct
    mc_ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]
    with TestingSessionLocal() as db:
        opt = db.query(MCAnswerOptionModel).first()
    client.post(
        f"/api/v1/assessments/exercise-attempts/{mc_ea_id}/mc-response",
        headers=teacher_headers, json={"selected_option_id": str(opt.id)},
    )

    # Submit OS correct
    os_ea_id = detail["exercise_attempts"][1]["exercise_attempt_id"]
    client.post(
        f"/api/v1/assessments/exercise-attempts/{os_ea_id}/os-response",
        headers=teacher_headers, json={"selected_syllables": ["sol"], "formed_word": "sol"},
    )

    # Submit Speaking
    sp_ea_id = detail["exercise_attempts"][2]["exercise_attempt_id"]
    client.post(
        f"/api/v1/assessments/exercise-attempts/{sp_ea_id}/speaking-response",
        headers=teacher_headers, files={"file": ("test.wav", b"fake", "audio/wav")},
    )

    # Finish
    finish = client.post(
        f"/api/v1/assessments/attempts/{attempt_id}/finish", headers=teacher_headers,
    )
    assert finish.status_code == 200
    finish_data = finish.json()

    # GET result
    get_resp = client.get(
        f"/api/v1/assessments/attempts/{attempt_id}/result", headers=teacher_headers,
    )
    assert get_resp.status_code == 200
    data = get_resp.json()

    assert data["total_exercises"] == 3, f"total_exercises={data['total_exercises']}"
    assert data["evaluated_exercises"] == 3, f"evaluated_exercises={data['evaluated_exercises']}"
    assert data["pending_exercises"] == 0, f"pending_exercises={data['pending_exercises']}"
    assert data["speaking_average_score"] is not None, "speaking_average_score should not be None"
    assert data["speaking_review_required_count"] == 0
    assert data["final_score"] is not None
    assert data["intervention_level"] == "LOW"
    assert data["mc_correct_count"] == 1
    assert data["os_correct_count"] == 1
    assert data["speaking_completed_count"] == 1

    # Consistency between POST finish and GET result
    for field in ("final_score", "mc_correct_count", "os_correct_count", "speaking_completed_count",
                  "intervention_level", "total_exercises", "evaluated_exercises", "pending_exercises"):
        assert data[field] == finish_data.get(field), f"Mismatch on {field}: POST={finish_data.get(field)} GET={data[field]}"


def test_get_mc_response_returns_saved_data(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TMCR", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex = client.post(
        "/api/v1/assessments/exercises", headers=teacher_headers, json={
            "type": "MULTIPLE_CHOICE", "title": "MC Get",
            "mc_question": {"question_text": "Q?", "options": [{"text": "A", "is_correct": True, "order_index": 1}]},
        }).json()

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": ex["exercise_id"], "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments", headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()

    att = client.post(
        f"/api/v1/assessments/{asm['assessment_id']}/attempts", headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()

    detail = client.get(
        f"/api/v1/assessments/attempts/{att['attempt_id']}", headers=teacher_headers
    ).json()
    ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]

    with TestingSessionLocal() as db:
        opt = db.query(MCAnswerOptionModel).first()

    submit = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/mc-response",
        headers=teacher_headers, json={"selected_option_id": str(opt.id)},
    )
    assert submit.status_code == 200

    get_resp = client.get(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/mc-response",
        headers=teacher_headers,
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["response_id"] is not None
    assert data["exercise_attempt_id"] == ea_id
    assert data["selected_option_id"] == str(opt.id)
    assert data["is_correct"] is True
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


def test_get_os_response_returns_saved_data(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TOSR", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex = client.post(
        "/api/v1/assessments/exercises", headers=teacher_headers, json={
            "type": "ORDER_SYLLABLES", "title": "OS Get",
            "os_question": {"question_text": "Ordena", "correct_word": "casa", "syllables_json": ["ca", "sa"]},
        }).json()

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": ex["exercise_id"], "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments", headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()

    att = client.post(
        f"/api/v1/assessments/{asm['assessment_id']}/attempts", headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()

    detail = client.get(
        f"/api/v1/assessments/attempts/{att['attempt_id']}", headers=teacher_headers
    ).json()
    ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]

    submit = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/os-response",
        headers=teacher_headers, json={"selected_syllables": ["ca", "sa"], "formed_word": "casa"},
    )
    assert submit.status_code == 200

    get_resp = client.get(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/os-response",
        headers=teacher_headers,
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["response_id"] is not None
    assert data["exercise_attempt_id"] == ea_id
    assert data["selected_syllables"] == ["ca", "sa"]
    assert data["formed_word"] == "casa"
    assert data["is_correct"] is True
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


def test_get_mc_response_not_found(client, teacher_headers):
    fake_id = uuid.uuid4()
    resp = client.get(
        f"/api/v1/assessments/exercise-attempts/{fake_id}/mc-response",
        headers=teacher_headers,
    )
    assert resp.status_code == 404


def test_get_os_response_not_found(client, teacher_headers):
    fake_id = uuid.uuid4()
    resp = client.get(
        f"/api/v1/assessments/exercise-attempts/{fake_id}/os-response",
        headers=teacher_headers,
    )
    assert resp.status_code == 404


def test_upload_mc_question_image(client, teacher_headers):
    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC Img",
            "mc_question": {
                "question_text": "¿Qué es?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()
    exercise_id = ex_resp["exercise_id"]

    response = client.post(
        f"/api/v1/assessments/exercises/{exercise_id}/mc-question/image",
        headers=teacher_headers,
        files={"file": ("test.png", b"fake-png-content", "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exercise_id"] == exercise_id
    assert data["mc_question_id"] is not None
    assert data["image_blob_path"] is not None
    assert "assessment-assets/exercises/" in data["image_blob_path"]
    assert data["content_type"] == "image/png"
    assert data["size_bytes"] == len(b"fake-png-content")


def test_upload_mc_question_image_wrong_exercise_type(client, teacher_headers):
    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "ORDER_SYLLABLES",
            "title": "OS Img",
            "os_question": {
                "question_text": "Ordena",
                "correct_word": "sol",
                "syllables_json": ["sol"],
            },
        },
    ).json()
    exercise_id = ex_resp["exercise_id"]

    response = client.post(
        f"/api/v1/assessments/exercises/{exercise_id}/mc-question/image",
        headers=teacher_headers,
        files={"file": ("test.png", b"fake", "image/png")},
    )
    assert response.status_code == 400
    assert "not MULTIPLE_CHOICE" in response.text


def test_upload_mc_question_image_invalid_content_type(client, teacher_headers):
    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC BadType",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()
    exercise_id = ex_resp["exercise_id"]

    response = client.post(
        f"/api/v1/assessments/exercises/{exercise_id}/mc-question/image",
        headers=teacher_headers,
        files={"file": ("test.gif", b"fake", "image/gif")},
    )
    assert response.status_code == 400


def test_upload_mc_question_image_exercise_not_found(client, teacher_headers):
    fake_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/assessments/exercises/{fake_id}/mc-question/image",
        headers=teacher_headers,
        files={"file": ("test.png", b"fake", "image/png")},
    )
    assert response.status_code == 404


def test_get_attempt_detail_returns_mc_image_blob_path_and_url(client, teacher_headers, classroom_id, student_id):
    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC Img Detail",
            "instructions": "Look at the image",
            "mc_question": {
                "question_text": "¿Qué ves?",
                "options": [
                    {"text": "Gato", "is_correct": True, "order_index": 1},
                    {"text": "Perro", "is_correct": False, "order_index": 2},
                ],
            },
        },
    ).json()
    exercise_id = ex_resp["exercise_id"]

    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TMCIMG", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": exercise_id, "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments", headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()

    att = client.post(
        f"/api/v1/assessments/{asm['assessment_id']}/attempts", headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()

    # Upload image to MC question
    client.post(
        f"/api/v1/assessments/exercises/{exercise_id}/mc-question/image",
        headers=teacher_headers,
        files={"file": ("test.png", b"fake-png-content", "image/png")},
    )

    detail = client.get(
        f"/api/v1/assessments/attempts/{att['attempt_id']}", headers=teacher_headers,
    )
    assert detail.status_code == 200
    items = detail.json()["exercise_attempts"]
    assert len(items) == 1
    ex = items[0]["exercise"]
    assert ex["type"] == "MULTIPLE_CHOICE"
    mc_q = ex["mc_question"]
    assert mc_q["question_text"] == "¿Qué ves?"
    assert mc_q["image_blob_path"] is not None
    assert "assessment-assets/exercises/" in mc_q["image_blob_path"]
    # image_url should be generated (non-null) because blob_path exists
    assert mc_q["image_url"] is not None, "image_url should be generated when image_blob_path exists"
    for opt in mc_q["options"]:
        assert "is_correct" not in opt, "is_correct must NOT be exposed"


# ─── Writing Response Tests ─────────────────────────────────────────────


SAMPLE_PAYLOAD_JSON = json.dumps({
    "canvas": {"width": 300, "height": 392, "device_pixel_ratio": 2.625},
    "input": {"pointer_kind": "touch", "supports_pressure": False},
    "strokes": [
        {
            "stroke_id": 1,
            "points": [
                {"x": 10.5, "y": 20.2, "t": 0, "pressure": None},
                {"x": 11.0, "y": 22.1, "t": 16, "pressure": None},
            ],
        },
        {
            "stroke_id": 2,
            "points": [
                {"x": 50.0, "y": 100.0, "t": 100, "pressure": None},
            ],
        },
    ],
    "metrics": {
        "duration_ms": 3500,
        "stroke_count": 2,
        "point_count": 3,
        "pause_count": 1,
        "longest_pause_ms": 600,
        "total_pause_time_ms": 600,
        "average_speed": 0.23,
        "speed_variability": 0.08,
        "bounding_box": {"min_x": 10.5, "min_y": 20.2, "max_x": 50.0, "max_y": 100.0},
        "writing_area_usage": 12.5,
        "pressure_min": None,
        "pressure_max": None,
        "pressure_avg": None,
    },
})


def _create_writing_setup(client, teacher_headers, classroom_id, student_id, exercise_type="READING_WRITING"):
    """Helper to create a template with one writing exercise, assessment, and attempt.
    Returns (attempt_id, exercise_attempt_id)."""
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TWRITE", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": exercise_type,
            "title": "Escritura digital",
            "instructions": "Copia la frase",
            "difficulty_level": 1,
            "prompt_exercise": {
                "text_to_show": "El gato duerme.",
                "language_code": "es-PE",
                "expected_text": "El gato duerme.",
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
    assessment_id = asm["assessment_id"]

    att = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()
    attempt_id = att["attempt_id"]

    detail = client.get(f"/api/v1/assessments/attempts/{attempt_id}", headers=teacher_headers).json()
    ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]
    return attempt_id, ea_id


# 1. POST writing-response with image + payload_json saves response
def test_upload_writing_response_creates_response(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["response_id"] is not None
    assert data["exercise_attempt_id"] == str(ea_id)
    assert data["image_blob_path"] is not None
    assert data["original_filename"] == "writing.png"
    assert data["content_type"] == "image/png"
    assert data["strokes_json"] is not None
    assert len(data["strokes_json"]) == 2
    assert data["canvas_metadata"]["width"] == 300
    assert data["input_metadata"]["pointer_kind"] == "touch"
    # POST must return metrics inline, not null
    assert data["metrics"] is not None, "POST writing-response must return metrics"
    assert data["metrics"]["duration_ms"] == 3500
    assert data["metrics"]["stroke_count"] == 2


# 2. POST writing-response sets ExerciseAttempt.status = ANSWERED
def test_upload_writing_response_sets_answered(client, teacher_headers, classroom_id, student_id):
    attempt_id, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    # Before upload, status should be PENDING
    detail = client.get(f"/api/v1/assessments/attempts/{attempt_id}", headers=teacher_headers).json()
    assert detail["exercise_attempts"][0]["status"] == "PENDING"

    client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )

    # After upload, status should be ANSWERED
    detail = client.get(f"/api/v1/assessments/attempts/{attempt_id}", headers=teacher_headers).json()
    assert detail["exercise_attempts"][0]["status"] == "ANSWERED"


# 3. POST writing-response sets submitted_at
def test_upload_writing_response_sets_submitted_at(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )
    assert resp.status_code == 200

    from app.assessment.infrastructure.models.attempt_model import ExerciseAttemptModel

    with TestingSessionLocal() as db:
        model = db.get(ExerciseAttemptModel, UUID(ea_id))
        assert model is not None
        assert model.submitted_at is not None


# 4. POST writing-response saves strokes_json
def test_upload_writing_response_saves_strokes(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )
    data = resp.json()
    assert len(data["strokes_json"]) == 2


# 5. POST writing-response saves Flutter metrics in WritingMetrics
def test_upload_writing_response_saves_metrics(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["metrics"] is not None
    assert data["metrics"]["duration_ms"] == 3500
    assert data["metrics"]["stroke_count"] == 2
    assert data["metrics"]["point_count"] == 3
    assert data["metrics"]["average_speed"] == 0.23
    assert data["metrics"]["pause_count"] == 1


# 6. GET writing-response returns image, strokes, and metrics
def test_get_writing_response_returns_data(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )

    get_resp = client.get(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["response_id"] is not None
    assert data["image_blob_path"] is not None
    assert data["image_url"] is not None
    assert data["strokes_json"] is not None
    assert data["metrics"] is not None
    assert data["canvas_metadata"]["width"] == 300


# 7. GET writing-response without response returns 404
def test_get_writing_response_not_found(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    get_resp = client.get(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
    )
    assert get_resp.status_code == 404
    assert "not found" in get_resp.json()["detail"].lower()


# 8. Reattempt writing overwrites previous response
def test_writing_reattempt_overwrites_previous(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    first_payload = json.dumps({"metrics": {"duration_ms": 1000, "stroke_count": 1}})
    client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("first.png", b"first-image", "image/png")},
        data={"payload_json": first_payload},
    )

    second_payload = json.dumps({"metrics": {"duration_ms": 5000, "stroke_count": 5}})
    client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("second.png", b"second-image", "image/png")},
        data={"payload_json": second_payload},
    )

    get_resp = client.get(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
    )
    data = get_resp.json()
    assert data["original_filename"] == "second.png"
    assert data["frontend_metrics"]["duration_ms"] == 5000
    assert data["metrics"]["stroke_count"] == 5


# 9. Finish with writing answered does not leave PENDING
def test_finish_with_writing_answered_not_pending(client, teacher_headers, classroom_id, student_id):
    attempt_id, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )

    finish = client.post(f"/api/v1/assessments/attempts/{attempt_id}/finish", headers=teacher_headers)
    assert finish.status_code == 200
    data = finish.json()
    assert data["writing_completed_count"] == 1
    assert data["pending_exercises"] == 0


# 10. Finish with writing without OCR does not lower final_score of MC/OS/Speaking
def test_finish_mixed_with_writing_does_not_lower_score(client, teacher_headers, classroom_id, student_id, monkeypatch):
    from app.assessment.application.use_cases.assess_reading_pipeline import AssessReadingPipelineUseCase

    async def mock_execute(self, command):
        return {
            "status": "completed",
            "recognized_text": "el gato",
            "stt_recognized_text": "el gato",
            "assessment_recognized_text": "El gato.",
            "pronunciation_score": 100.0,
            "accuracy_score": 100.0,
            "fluency_score": 100.0,
            "completeness_score": 100.0,
            "prosody_score": None,
            "comparison": None,
            "review": {},
            "error_message": None,
            "duration_ms": 2000,
            "raw_result_json": {},
            "stt": {"text": "el gato", "segments": [], "language": "es", "duration_ms": 2000},
        }

    monkeypatch.setattr(AssessReadingPipelineUseCase, "execute", mock_execute)

    # Create template with MC, OS, Speaking, Writing
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TMIXW", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    mc_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()
    os_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "ORDER_SYLLABLES",
            "title": "OS",
            "os_question": {
                "question_text": "Ordena",
                "correct_word": "sol",
                "syllables_json": ["sol"],
            },
        },
    ).json()
    sp_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "READING_SPEAKING",
            "title": "Speaking",
            "prompt_exercise": {
                "text_to_show": "El gato",
                "language_code": "es-PE",
                "expected_text": "El gato.",
            },
        },
    ).json()
    wr_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "READING_WRITING",
            "title": "Writing",
            "prompt_exercise": {
                "text_to_show": "El gato duerme.",
                "language_code": "es-PE",
                "expected_text": "El gato duerme.",
            },
        },
    ).json()

    for ex_id, idx in [
        (mc_resp["exercise_id"], 1),
        (os_resp["exercise_id"], 2),
        (sp_resp["exercise_id"], 3),
        (wr_resp["exercise_id"], 4),
    ]:
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

    att = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()
    attempt_id = att["attempt_id"]

    detail = client.get(f"/api/v1/assessments/attempts/{attempt_id}", headers=teacher_headers).json()

    # Submit MC (correct)
    mc_ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]
    with TestingSessionLocal() as db:
        option = db.query(MCAnswerOptionModel).first()
        option_id = option.id
    client.post(
        f"/api/v1/assessments/exercise-attempts/{mc_ea_id}/mc-response",
        headers=teacher_headers,
        json={"selected_option_id": str(option_id)},
    )

    # Submit OS (correct)
    os_ea_id = detail["exercise_attempts"][1]["exercise_attempt_id"]
    client.post(
        f"/api/v1/assessments/exercise-attempts/{os_ea_id}/os-response",
        headers=teacher_headers,
        json={"selected_syllables": ["sol"], "formed_word": "sol"},
    )

    # Submit Speaking
    sp_ea_id = detail["exercise_attempts"][2]["exercise_attempt_id"]
    client.post(
        f"/api/v1/assessments/exercise-attempts/{sp_ea_id}/speaking-response",
        headers=teacher_headers,
        files={"file": ("test.wav", b"fake audio", "audio/wav")},
    )

    # Submit Writing (without OCR)
    wr_ea_id = detail["exercise_attempts"][3]["exercise_attempt_id"]
    client.post(
        f"/api/v1/assessments/exercise-attempts/{wr_ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )

    # Finish
    finish = client.post(f"/api/v1/assessments/attempts/{attempt_id}/finish", headers=teacher_headers)
    assert finish.status_code == 200
    data = finish.json()
    # MC=100, OS=100, Speaking=100 -> avg = 100
    # Writing should NOT be in denominator
    assert data["final_score"] == 100.0
    assert data["writing_completed_count"] == 1
    assert data["mc_correct_count"] == 1
    assert data["os_correct_count"] == 1
    assert data["speaking_completed_count"] == 1
    assert data["total_exercises"] == 4
    assert data["evaluated_exercises"] == 4
    assert data["pending_exercises"] == 0


# 11. Upload writing on non-writing exercise returns 400
def test_upload_writing_wrong_exercise_type_returns_400(client, teacher_headers, classroom_id, student_id):
    tmpl_resp = client.post(
        "/api/v1/assessments/templates", headers=teacher_headers, json={"name": "TMC", "version": 1}
    )
    template_id = tmpl_resp.json()["template_id"]

    ex_resp = client.post(
        "/api/v1/assessments/exercises",
        headers=teacher_headers,
        json={
            "type": "MULTIPLE_CHOICE",
            "title": "MC",
            "mc_question": {
                "question_text": "Q?",
                "options": [{"text": "A", "is_correct": True, "order_index": 1}],
            },
        },
    ).json()

    client.post(
        f"/api/v1/assessments/templates/{template_id}/exercises",
        headers=teacher_headers,
        json={"exercise_id": ex_resp["exercise_id"], "order_index": 1, "points": 10, "is_required": True},
    )

    asm = client.post(
        "/api/v1/assessments",
        headers=teacher_headers,
        json={"template_id": template_id, "classroom_id": str(classroom_id)},
    ).json()
    assessment_id = asm["assessment_id"]

    att = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers=teacher_headers,
        json={"student_id": str(student_id)},
    ).json()
    attempt_id = att["attempt_id"]

    detail = client.get(f"/api/v1/assessments/attempts/{attempt_id}", headers=teacher_headers).json()
    ea_id = detail["exercise_attempts"][0]["exercise_attempt_id"]

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )
    assert resp.status_code == 400
    assert "writing" in resp.json()["detail"].lower()


# 12. Upload with invalid content type returns 400
def test_upload_writing_invalid_content_type_returns_400(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.gif", b"fake-gif-content", "image/gif")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )
    assert resp.status_code == 400
    assert "image format" in resp.json()["detail"].lower()


# 13. Upload with invalid payload_json returns 400
def test_upload_writing_invalid_payload_json_returns_400(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": "not-valid-json"},
    )
    assert resp.status_code == 400
    assert "valid json" in resp.json()["detail"].lower()


# 14. Only writing exercises are allowed
def test_upload_writing_listening_writing_is_accepted(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id, exercise_type="LISTENING_WRITING")

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )
    assert resp.status_code == 200


# 15. Finish all writing exercises (no scored exercises) returns None score
def test_finish_all_writing_returns_null_score(client, teacher_headers, classroom_id, student_id):
    attempt_id, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )

    finish = client.post(f"/api/v1/assessments/attempts/{attempt_id}/finish", headers=teacher_headers)
    assert finish.status_code == 200
    data = finish.json()
    assert data["final_score"] is None
    assert data["max_score"] is None
    assert data["writing_completed_count"] == 1
    assert data["total_exercises"] == 1
    assert data["evaluated_exercises"] == 1
    assert data["pending_exercises"] == 0
    assert data["intervention_level"] is None, "intervention_level should be null when no scored exercises"


# 16. WebP image is accepted
def test_upload_writing_webp_accepted(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.webp", b"fake-webp-content", "image/webp")},
        data={"payload_json": SAMPLE_PAYLOAD_JSON},
    )
    assert resp.status_code == 200


# 17. payload_json without metrics still saves response
def test_upload_writing_without_metrics_still_succeeds(client, teacher_headers, classroom_id, student_id):
    _, ea_id = _create_writing_setup(client, teacher_headers, classroom_id, student_id)

    minimal_payload = json.dumps({"strokes": []})
    resp = client.post(
        f"/api/v1/assessments/exercise-attempts/{ea_id}/writing-response",
        headers=teacher_headers,
        files={"file": ("writing.png", b"fake-png-content", "image/png")},
        data={"payload_json": minimal_payload},
    )
    assert resp.status_code == 200
