from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class MCResponse:
    id: UUID
    exercise_attempt_id: UUID
    selected_option_id: UUID
    is_correct: bool | None
    created_at: datetime
    updated_at: datetime


@dataclass
class OSResponse:
    id: UUID
    exercise_attempt_id: UUID
    selected_syllables_json: list[str]
    formed_word: str | None
    is_correct: bool | None
    created_at: datetime
    updated_at: datetime


@dataclass
class SpeakingResponse:
    id: UUID
    exercise_attempt_id: UUID
    audio_blob_path: str
    original_filename: str | None
    content_type: str | None
    duration_ms: int | None
    recognized_text: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class WritingResponse:
    id: UUID
    exercise_attempt_id: UUID
    image_blob_path: str
    original_filename: str | None
    content_type: str | None
    recognized_text: str | None
    created_at: datetime
    updated_at: datetime
