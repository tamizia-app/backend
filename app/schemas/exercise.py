from app.domain.enums import ExerciseType
from app.schemas.common import TimestampedModel


class ExerciseResponse(TimestampedModel):
    type: ExerciseType
    title: str
    instructions: str
    reference_text: str
    difficulty_level: int
    is_active: bool

