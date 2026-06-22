from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class StudentResult:
    student_id: UUID
    classroom_id: UUID
    code: str
    age: int
    gender: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class StudentConsentResult:
    consent_id: UUID
    student_id: UUID
    status: bool
    consent_date: datetime | None
    revoked_at: datetime | None
    evidence_blob_path: str | None
    created_at: datetime
    updated_at: datetime
