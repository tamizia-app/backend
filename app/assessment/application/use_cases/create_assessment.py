from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from app.assessment.application.assemblers import AssessmentAssembler
from app.assessment.application.exceptions import TeacherNotOwnerError
from app.assessment.application.ports.repositories import AssessmentRepository, TemplateRepository
from app.assessment.application.results import AssessmentResult
from app.assessment.domain.assessment import Assessment
from app.assessment.domain.enums import AssessmentStatus
from app.school.application.ports.classroom_repository import ClassroomRepository


@dataclass
class CreateAssessmentCommand:
    template_id: UUID
    classroom_id: UUID
    homeroom_teacher_id: UUID
    title: str | None
    scheduled_at: date | None


class CreateAssessmentUseCase:
    def __init__(
        self,
        assessment_repo: AssessmentRepository,
        template_repo: TemplateRepository,
        classroom_repo: ClassroomRepository,
    ) -> None:
        self._assessment_repo = assessment_repo
        self._template_repo = template_repo
        self._classroom_repo = classroom_repo

    def execute(self, command: CreateAssessmentCommand) -> AssessmentResult:
        classroom = self._classroom_repo.find_by_id(command.classroom_id)
        if not classroom:
            raise TeacherNotOwnerError("Classroom not found.")

        if classroom.homeroom_teacher_id != command.homeroom_teacher_id:
            raise TeacherNotOwnerError()

        now = datetime.now(timezone.utc)
        assessment = self._assessment_repo.create(
            Assessment(
                id=UUID(int=0),
                template_id=command.template_id,
                classroom_id=command.classroom_id,
                homeroom_teacher_id=command.homeroom_teacher_id,
                title=command.title,
                status=AssessmentStatus.DRAFT,
                scheduled_at=command.scheduled_at,
                created_at=now,
                updated_at=now,
            )
        )
        return AssessmentAssembler.to_result(assessment)
