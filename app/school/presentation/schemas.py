from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.school.domain.enums import GradeLevel, Section


class HomeroomTeacherResponse(BaseModel):
    teacher_id: UUID
    name: str
    lastname: str
    email: str
    institute_name: str | None
    phone: str | None


class UpdateHomeroomTeacherRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    lastname: str = Field(min_length=1, max_length=255)
    email: EmailStr
    institute_name: str | None = None
    phone: str | None = None


class CreateClassroomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    grade_level: GradeLevel
    section: Section
    school_year: date


class UpdateClassroomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    grade_level: GradeLevel
    section: Section
    school_year: date


class ClassroomResponse(BaseModel):
    classroom_id: UUID
    homeroom_teacher_id: UUID
    name: str
    grade_level: str
    section: str
    school_year: date
