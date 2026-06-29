from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentRepository,
    AssessmentResultRepository,
)
from app.assessment.domain.enums import ExerciseAttemptStatus


@dataclass
class StudentAssessmentHistoryItem:
    attempt_id: UUID
    assessment_id: UUID
    assessment_name: str | None
    status: str
    started_at: datetime
    completed_at: datetime | None
    final_score: float | None
    max_score: float | None
    intervention_level: str | None
    mc_correct_count: int | None
    os_correct_count: int | None
    speaking_completed_count: int | None
    speaking_average_score: float | None
    speaking_review_required_count: int
    writing_completed_count: int | None
    writing_average_score: float | None
    writing_review_required_count: int
    total_exercises: int
    evaluated_exercises: int
    pending_exercises: int


@dataclass
class StudentAssessmentHistorySummary:
    attempts_count: int
    completed_attempts_count: int
    latest_score: float | None
    average_score: float | None
    best_score: float | None
    lowest_score: float | None
    trend_percentage: float | None
    latest_intervention_level: str | None
    latest_completed_at: datetime | None


@dataclass
class StudentAssessmentHistoryResult:
    student_id: UUID
    summary: StudentAssessmentHistorySummary
    items: list[StudentAssessmentHistoryItem]


@dataclass
class GetStudentAssessmentHistoryQuery:
    student_id: UUID
    limit: int = 20
    offset: int = 0
    status: str | None = "COMPLETED"
    assessment_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class GetStudentAssessmentHistoryUseCase:
    def __init__(
        self,
        attempt_repo: AssessmentAttemptRepository,
        result_repo: AssessmentResultRepository,
        assessment_repo: AssessmentRepository,
    ) -> None:
        self._attempt_repo = attempt_repo
        self._result_repo = result_repo
        self._assessment_repo = assessment_repo

    def execute(self, query: GetStudentAssessmentHistoryQuery) -> StudentAssessmentHistoryResult:
        attempts = self._attempt_repo.find_by_student_id(
            query.student_id,
            status=query.status,
            assessment_id=query.assessment_id,
            date_from=query.date_from,
            date_to=query.date_to,
            limit=query.limit,
            offset=query.offset,
        )

        items: list[StudentAssessmentHistoryItem] = []
        completed_scores: list[float] = []
        completed_at_list: list[datetime] = []

        for attempt in attempts:
            result = self._result_repo.find_by_attempt_id(attempt.id)

            assessment_name = None
            assessment = self._assessment_repo.find_by_id(attempt.assessment_id)
            if assessment:
                assessment_name = assessment.title or "Untitled"

            if result:
                if attempt.status.value == "COMPLETED" and result.final_score is not None:
                    completed_scores.append(result.final_score)
                    if attempt.completed_at:
                        completed_at_list.append(attempt.completed_at)

            item = StudentAssessmentHistoryItem(
                attempt_id=attempt.id,
                assessment_id=attempt.assessment_id,
                assessment_name=assessment_name,
                status=attempt.status.value,
                started_at=attempt.started_at,
                completed_at=attempt.completed_at,
                final_score=result.final_score if result else None,
                max_score=result.max_score if result else None,
                intervention_level=result.intervention_level.value if result and result.intervention_level else None,
                mc_correct_count=result.mc_correct_count if result else None,
                os_correct_count=result.os_correct_count if result else None,
                speaking_completed_count=result.speaking_completed_count if result else None,
                speaking_average_score=result.speaking_average_score if result else None,
                speaking_review_required_count=result.speaking_review_required_count if result else 0,
                writing_completed_count=result.writing_completed_count if result else None,
                writing_average_score=result.writing_average_score if result else None,
                writing_review_required_count=result.writing_review_required_count if result else 0,
                total_exercises=result.total_exercises if result else 0,
                evaluated_exercises=result.evaluated_exercises if result else 0,
                pending_exercises=result.total_exercises - result.evaluated_exercises if result else 0,
            )
            items.append(item)

        summary = self._build_summary(completed_scores, completed_at_list, items)
        return StudentAssessmentHistoryResult(
            student_id=query.student_id,
            summary=summary,
            items=items,
        )

    def _build_summary(self, scores, completed_at_list, items):
        completed_count = len(scores)
        latest_score = scores[-1] if scores else None
        latest_completed_at = completed_at_list[-1] if completed_at_list else None
        average_score = sum(scores) / len(scores) if scores else None
        best_score = max(scores) if scores else None
        lowest_score = min(scores) if scores else None

        trend_percentage = None
        if len(scores) >= 2:
            prev = scores[-2]
            if prev > 0:
                trend_percentage = round((scores[-1] - prev) / prev * 100, 2)

        latest_intervention_level = None
        for item in reversed(items):
            if item.intervention_level:
                latest_intervention_level = item.intervention_level
                break

        return StudentAssessmentHistorySummary(
            attempts_count=len(items),
            completed_attempts_count=completed_count,
            latest_score=latest_score,
            average_score=average_score,
            best_score=best_score,
            lowest_score=lowest_score,
            trend_percentage=trend_percentage,
            latest_intervention_level=latest_intervention_level,
            latest_completed_at=latest_completed_at,
        )
