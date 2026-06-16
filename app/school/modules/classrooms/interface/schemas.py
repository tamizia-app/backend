from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    grade_level: str = Field(min_length=1, max_length=50)
    section: str | None = Field(default=None, max_length=50)
    school_year: str = Field(min_length=1, max_length=20)


class ClassroomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    grade_level: str | None = Field(default=None, min_length=1, max_length=50)
    section: str | None = Field(default=None, max_length=50)
    school_year: str | None = Field(default=None, min_length=1, max_length=20)
    is_active: bool | None = None


class ClassroomResponse(TimestampedModel):
    name: str
    grade_level: str
    section: str | None
    school_year: str
    is_active: bool
