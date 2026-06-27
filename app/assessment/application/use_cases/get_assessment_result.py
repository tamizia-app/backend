from dataclasses import dataclass
from uuid import UUID

from app.assessment.application.assemblers import FinalResultAssembler
from app.assessment.application.exceptions import AttemptNotFoundError
from app.assessment.application.ports.repositories import AssessmentAttemptRepository, AssessmentResultRepository
from app.assessment.application.results import FinalResult


@dataclass
class GetAssessmentResultQuery:
    attempt_id: UUID


class GetAssessmentResultUseCase:
    def __init__(
        self,
        attempt_repo: AssessmentAttemptRepository,
        result_repo: AssessmentResultRepository,
    ) -> None:
        self._attempt_repo = attempt_repo
        self._result_repo = result_repo

    def execute(self, query: GetAssessmentResultQuery) -> FinalResult:
        attempt = self._attempt_repo.find_by_id(query.attempt_id)
        if not attempt:
            raise AttemptNotFoundError()

        result = self._result_repo.find_by_attempt_id(query.attempt_id)
        if not result:
            raise AttemptNotFoundError("Result not yet generated. Finish the attempt first.")

        return FinalResultAssembler.to_result(result)
