from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.school.domain.enums import Gender


@dataclass
class Student:
    id: UUID
    classroom_id: UUID
    code: str
    age: int
    gender: Gender
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class StudentConsent:
    id: UUID
    student_id: UUID
    status: bool
    consent_date: datetime | None
    revoked_at: datetime | None
    evidence_blob_path: str | None
    created_at: datetime
    updated_at: datetime
