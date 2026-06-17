from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.school.domain.enums import GradeLevel, Section


@dataclass
class Classroom:
    id: UUID
    homeroom_teacher_id: UUID
    name: str
    grade_level: GradeLevel
    section: Section
    school_year: date
    is_active: bool
    created_at: datetime
    updated_at: datetime
