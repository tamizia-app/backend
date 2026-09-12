from dataclasses import dataclass, replace
from uuid import UUID

from app.assessment.application.assemblers import TemplateAssembler
from app.assessment.application.exceptions import TemplateNotFoundError
from app.assessment.application.ports.repositories import TemplateRepository
from app.assessment.application.results import TemplateResult


@dataclass
class SetTemplateActiveCommand:
    template_id: UUID
    teacher_id: UUID
    is_active: bool


class SetTemplateActiveUseCase:
    def __init__(self, template_repo: TemplateRepository) -> None:
        self._template_repo = template_repo

    def execute(self, command: SetTemplateActiveCommand) -> TemplateResult:
        template = self._template_repo.find_owned_by_id(command.template_id, command.teacher_id)
        if not template:
            raise TemplateNotFoundError()

        updated = self._template_repo.update(
            replace(template, is_active=command.is_active)
        )
        return TemplateAssembler.to_result(updated)
