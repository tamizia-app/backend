from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.assessment.domain.enums import (
    AssessmentStatus,
    AttemptStatus,
    ExerciseAttemptStatus,
    ExerciseType,
    InterventionLevel,
)


@dataclass
class TemplateResult:
    template_id: UUID
    name: str
    description: str | None
    version: int
    is_active: bool
    created_by_teacher_id: UUID | None
    created_at: datetime
    updated_at: datetime
    exercises: list["TemplateExerciseResult"] | None = None


@dataclass
class TemplateExerciseResult:
    template_exercise_id: UUID
    exercise_id: UUID
    order_index: int
    points: int
    is_required: bool


@dataclass
class ExerciseResult:
    exercise_id: UUID
    type: ExerciseType
    title: str
    instructions: str | None
    stimulus_type: str | None
    response_type: str | None
    difficulty_level: int | None
    is_active: bool
    created_by_teacher_id: UUID | None
    created_at: datetime
    updated_at: datetime


@dataclass
class AssessmentResult:
    assessment_id: UUID
    template_id: UUID
    classroom_id: UUID
    homeroom_teacher_id: UUID
    title: str | None
    status: AssessmentStatus
    scheduled_at: date | None
    created_at: datetime
    updated_at: datetime


@dataclass
class AttemptResult:
    attempt_id: UUID
    assessment_id: UUID
    student_id: UUID
    status: AttemptStatus
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    exercise_attempts: list["ExerciseAttemptResult"] | None = None


@dataclass
class ExerciseAttemptResult:
    exercise_attempt_id: UUID
    template_exercise_id: UUID
    status: ExerciseAttemptStatus
    started_at: datetime | None
    submitted_at: datetime | None


@dataclass
class MCResponseResult:
    response_id: UUID
    exercise_attempt_id: UUID
    selected_option_id: UUID
    is_correct: bool | None


@dataclass
class OSResponseResult:
    response_id: UUID
    exercise_attempt_id: UUID
    selected_syllables: list[str]
    formed_word: str | None
    is_correct: bool | None


@dataclass
class SpeakingResponseResult:
    response_id: UUID
    exercise_attempt_id: UUID
    audio_blob_path: str
    original_filename: str | None
    content_type: str | None
    duration_ms: int | None
    free_transcription_text: str | None = None
    assessment_recognized_text: str | None = None
    recognized_text: str | None = None
    pronunciation_score: float | None = None
    accuracy_score: float | None = None
    fluency_score: float | None = None
    completeness_score: float | None = None
    prosody_score: float | None = None
    evaluation_status: str = "completed"
    comparison: dict | None = None
    review: dict | None = None
    error_message: str | None = None


@dataclass
class WritingResponseResult:
    response_id: UUID
    exercise_attempt_id: UUID
    image_blob_path: str
    original_filename: str | None
    content_type: str | None
    recognized_text: str | None = None
    strokes_json: dict | None = None
    canvas_metadata_json: dict | None = None
    input_metadata_json: dict | None = None
    frontend_metrics_json: dict | None = None
    metrics: dict | None = None
    image_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class FinalResult:
    attempt_id: UUID
    final_score: float | None
    max_score: float | None
    mc_correct_count: int | None
    os_correct_count: int | None
    speaking_completed_count: int | None
    writing_completed_count: int | None
    intervention_level: InterventionLevel | None
    generated_at: datetime | None
    speaking_average_score: float | None = None
    speaking_review_required_count: int = 0
    total_exercises: int = 0
    evaluated_exercises: int = 0
    pending_exercises: int = 0
    writing_average_score: float | None = None
    writing_review_required_count: int = 0
