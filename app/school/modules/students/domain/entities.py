from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class StudentData:
    code: str
    first_name: str
    last_name: str
    age: int


@dataclass(frozen=True)
class StudentIdentity:
    id: UUID
    classroom_id: UUID

