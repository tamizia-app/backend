from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class PromptExercise:
    id: UUID
    exercise_id: UUID
    prompt_text: str | None
    text_to_show: str | None
    audio_blob_path: str | None
    image_blob_path: str | None
    language_code: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ExpectedAnswer:
    id: UUID
    prompt_exercise_id: UUID
    expected_text: str
    created_at: datetime
    updated_at: datetime
