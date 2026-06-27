from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.assessment.application.assemblers import TemplateAssembler
from app.assessment.application.ports.repositories import TemplateRepository
from app.assessment.application.results import TemplateResult
from app.assessment.domain.template import AssessmentTemplate


@dataclass
class CreateTemplateCommand:
    name: str
    description: str | None
    version: int
    created_by_teacher_id: UUID | None


class CreateTemplateUseCase:
    def __init__(self, template_repo: TemplateRepository) -> None:
        self._template_repo = template_repo

    def execute(self, command: CreateTemplateCommand) -> TemplateResult:
        now = datetime.now(timezone.utc)
        template = self._template_repo.create(
            AssessmentTemplate(
                id=UUID(int=0),
                name=command.name,
                description=command.description,
                version=command.version,
                is_active=True,
                created_by_teacher_id=command.created_by_teacher_id,
                created_at=now,
                updated_at=now,
            )
        )
        return TemplateAssembler.to_result(template)
