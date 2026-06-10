from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class SignupResult:
    user_id: UUID
    teacher_id: UUID
    name: str
    lastname: str
    email: str
    institute_name: str | None
    phone: str | None
    created_at: datetime
