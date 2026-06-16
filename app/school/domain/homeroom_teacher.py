from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class HomeroomTeacher:
    id: UUID
    user_id: UUID
    institute_name: str | None
    phone: str | None
    created_at: datetime
    updated_at: datetime
