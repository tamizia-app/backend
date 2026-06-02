from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.results.domain.exceptions import ResultNotFoundError
from app.modules.results.domain.repositories import ResultRepository


@dataclass(frozen=True)
class GetResultBySessionQuery:
    session_id: UUID
    current_user: Any


class GetResultBySessionUseCase:
    def __init__(self, repository: ResultRepository) -> None:
        self.repository = repository

    def execute(self, query: GetResultBySessionQuery):
        result = self.repository.get_by_session(query.session_id)
        if not result:
            raise ResultNotFoundError()
        return result

