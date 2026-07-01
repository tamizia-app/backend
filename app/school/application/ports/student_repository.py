from typing import Protocol
from uuid import UUID

from app.school.domain.student import Student


class StudentRepository(Protocol):
    def find_by_id(self, student_id: UUID) -> Student | None: ...
    def find_by_classroom_id(self, classroom_id: UUID) -> list[Student]: ...
    def find_by_code_in_classroom(self, code: str, classroom_id: UUID, exclude_id: UUID | None = None) -> Student | None: ...
    def find_by_code(self, code: str) -> Student | None: ...
    def find_by_teacher_id(
        self,
        teacher_id: UUID,
        *,
        classroom_id: UUID | None = None,
        q: str | None = None,
        is_active: bool | None = True,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Student]: ...
    def count_by_teacher_id(
        self,
        teacher_id: UUID,
        *,
        classroom_id: UUID | None = None,
        q: str | None = None,
        is_active: bool | None = True,
    ) -> int: ...
    def create(self, student: Student) -> Student: ...
    def update(self, student: Student) -> Student: ...
    def delete(self, student_id: UUID) -> None: ...
