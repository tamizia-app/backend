from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.results.domain.repositories import ResultRepository


@dataclass(frozen=True)
class ListStudentResultHistoryQuery:
    student_id: UUID
    current_user: Any


class ListStudentResultHistoryUseCase:
    def __init__(self, repository: ResultRepository) -> None:
        self.repository = repository

    def execute(self, query: ListStudentResultHistoryQuery):
        return self.repository.list_by_student(query.student_id)

