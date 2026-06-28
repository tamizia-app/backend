from __future__ import annotations

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
