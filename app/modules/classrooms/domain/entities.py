from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassroomData:
    name: str
    grade_level: str
    section: str | None
    school_year: str

