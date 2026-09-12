from dataclasses import dataclass
from uuid import UUID

from app.assessment.application.exceptions import TemplateHasHistoryError, TemplateNotFoundError
from app.assessment.application.ports.repositories import TemplateExerciseRepository, TemplateRepository


@dataclass
class DeleteTemplateCommand:
    template_id: UUID
    teacher_id: UUID


class DeleteTemplateUseCase:
    def __init__(
        self,
        template_repo: TemplateRepository,
        template_exercise_repo: TemplateExerciseRepository,
    ) -> None:
        self._template_repo = template_repo
        self._template_exercise_repo = template_exercise_repo

    def execute(self, command: DeleteTemplateCommand) -> None:
        template = self._template_repo.find_owned_by_id(command.template_id, command.teacher_id)
        if not template:
            raise TemplateNotFoundError()

        if self._template_repo.has_history(command.template_id):
            raise TemplateHasHistoryError()

        self._template_exercise_repo.delete_by_template_id(command.template_id)
        self._template_repo.delete(command.template_id)
