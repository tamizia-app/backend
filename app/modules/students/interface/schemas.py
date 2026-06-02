from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


class StudentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=4, le=18)


class StudentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    age: int | None = Field(default=None, ge=4, le=18)
    is_active: bool | None = None


class StudentResponse(TimestampedModel):
    classroom_id: UUID
    code: str
    first_name: str
    last_name: str
    age: int
    is_active: bool
