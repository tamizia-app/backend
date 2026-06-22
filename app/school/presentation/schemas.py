from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.school.domain.enums import Gender, GradeLevel, Section


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


class CreateStudentRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=4, le=18)
    gender: Gender


class UpdateStudentRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=4, le=18)
    gender: Gender


class StudentResponse(BaseModel):
    student_id: UUID
    classroom_id: UUID
    code: str
    age: int
    gender: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StudentConsentResponse(BaseModel):
    consent_id: UUID
    student_id: UUID
    status: bool
    consent_date: datetime | None
    revoked_at: datetime | None
    evidence_blob_path: str | None
    created_at: datetime
    updated_at: datetime
