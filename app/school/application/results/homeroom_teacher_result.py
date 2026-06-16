from dataclasses import dataclass
from uuid import UUID


@dataclass
class HomeroomTeacherResult:
    teacher_id: UUID
    name: str
    lastname: str
    email: str
    institute_name: str | None
    phone: str | None
