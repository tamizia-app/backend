from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.dependencies.services import get_ocr_service, get_pronunciation_service, get_storage_service
from app.domain.enums import ExerciseType, UserRole
from app.main import app
from app.models.exercise import Exercise
from app.models.teacher_profile import TeacherProfile
from app.models.user import User
from app.services.azure.ocr import OCRServiceResult
from app.services.azure.speech import PronunciationServiceResult
from app.services.azure.storage import ObjectStorageService


SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class MockOCRService:
    def analyze_image(self, image_bytes: bytes) -> OCRServiceResult:
        return OCRServiceResult(
            extracted_text="Mi casa tiene una ventana azul.",
            confidence_avg=0.98,
            raw_response={"provider": "mock-ocr"},
        )


class MockPronunciationService:
    def analyze_audio(self, *, audio_bytes: bytes, reference_text: str, locale: str) -> PronunciationServiceResult:
        return PronunciationServiceResult(
            accuracy_score=87.0,
            fluency_score=84.0,
            completeness_score=90.0,
            pronunciation_score=86.0,
            recognized_text=reference_text,
            raw_response={"provider": "mock-speech", "locale": locale},
        )


@pytest.fixture(autouse=True)
def setup_database(tmp_path: Path) -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        teacher = User(
            email="teacher@example.com",
            password_hash=hash_password("secret123"),
            full_name="Teacher One",
            role=UserRole.TEACHER,
        )
        other_teacher = User(
            email="other@example.com",
            password_hash=hash_password("secret123"),
            full_name="Teacher Two",
            role=UserRole.TEACHER,
        )
        db.add_all([teacher, other_teacher])
        db.flush()
        db.add_all(
            [
                TeacherProfile(user_id=teacher.id, institution_name="Colegio Demo"),
                TeacherProfile(user_id=other_teacher.id, institution_name="Colegio Demo"),
            ]
        )
        db.add_all(
            [
                Exercise(
                    id=UUID("11111111-1111-1111-1111-111111111111"),
                    type=ExerciseType.WRITING,
                    title="Copia de frase corta",
                    instructions="Copia la frase",
                    reference_text="Mi casa tiene una ventana azul.",
                    difficulty_level=1,
                    is_active=True,
                ),
                Exercise(
                    id=UUID("22222222-2222-2222-2222-222222222222"),
                    type=ExerciseType.READING,
                    title="Lectura de frase",
                    instructions="Lee la frase",
                    reference_text="El perro corre por el patio.",
                    difficulty_level=1,
                    is_active=True,
                ),
                Exercise(
                    id=UUID("33333333-3333-3333-3333-333333333333"),
                    type=ExerciseType.COMBINED,
                    title="Lectura y copia",
                    instructions="Lee y escribe",
                    reference_text="La luna brilla sobre el lago tranquilo.",
                    difficulty_level=2,
                    is_active=True,
                ),
            ]
        )
        db.commit()

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    storage_service = ObjectStorageService(
        settings=type(
            "TestSettings",
            (),
            {
                "azure_blob_connection_string": None,
                "azure_blob_container": "test",
                "local_storage_path": str(tmp_path / "storage"),
            },
        )()
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = lambda: storage_service
    app.dependency_overrides[get_ocr_service] = lambda: MockOCRService()
    app.dependency_overrides[get_pronunciation_service] = lambda: MockPronunciationService()

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def auth_headers(client: TestClient, email: str = "teacher@example.com", password: str = "secret123") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def teacher_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client)


@pytest.fixture
def other_teacher_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client, email="other@example.com")
