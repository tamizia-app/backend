from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class OSQuestion:
    id: UUID
    exercise_id: UUID
    question_text: str
    image_blob_path: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class OSAnswer:
    id: UUID
    os_question_id: UUID
    correct_word: str
    syllables_json: list[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class MCQuestion:
    id: UUID
    exercise_id: UUID
    question_text: str
    image_blob_path: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class MCAnswerOption:
    id: UUID
    mc_question_id: UUID
    text: str
    is_correct: bool
    order_index: int
    created_at: datetime
    updated_at: datetime
