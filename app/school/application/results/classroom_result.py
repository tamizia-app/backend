from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass
class ClassroomResult:
    classroom_id: UUID
    homeroom_teacher_id: UUID
    name: str
    grade_level: str
    section: str
    school_year: date
