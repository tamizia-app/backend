from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.assessment.domain.enums import AssessmentStatus


@dataclass
class Assessment:
    id: UUID
    template_id: UUID
    classroom_id: UUID
    homeroom_teacher_id: UUID
    title: str | None
    status: AssessmentStatus
    scheduled_at: date | None
    created_at: datetime
    updated_at: datetime
