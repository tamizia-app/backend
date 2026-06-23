from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.shared.base import Base
from app.db.session import get_db
from app.iam.domain.enums import UserRole
from app.main import app
from app.models.teacher_profile import TeacherProfile
from app.models.user import User


SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


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
        db.commit()

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


def auth_headers(client: TestClient, email: str = "teacher@example.com", password: str = "secret123") -> dict[str, str]:
    response = client.post("/api/v1/auth/signin", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def teacher_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client)


@pytest.fixture
def other_teacher_headers(client: TestClient) -> dict[str, str]:
    return auth_headers(client, email="other@example.com")
