from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TeacherResponse(BaseModel):
    teacher_id: UUID
    name: str
    lastname: str
    email: str
    institute_name: str | None
    phone: str | None


class UpdateTeacherRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    lastname: str = Field(min_length=1, max_length=255)
    email: EmailStr
    institute_name: str | None = None
    phone: str | None = None
