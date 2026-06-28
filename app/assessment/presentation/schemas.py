from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.assessment.domain.enums import ExerciseType


class CreateTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    version: int = Field(default=1, ge=1)


class TemplateResponse(BaseModel):
    template_id: UUID
    name: str
    description: str | None
    version: int
    is_active: bool
    created_by_teacher_id: UUID | None
    created_at: datetime
    updated_at: datetime


class MCAnswerOptionData(BaseModel):
    text: str = Field(min_length=1, max_length=255)
    is_correct: bool = False
    order_index: int


class MCQuestionData(BaseModel):
    question_text: str
    image_blob_path: str | None = None
    options: list[MCAnswerOptionData] = Field(min_length=1)


class OSQuestionData(BaseModel):
    question_text: str
    image_blob_path: str | None = None
    correct_word: str
    syllables_json: list[str]


class PromptExerciseData(BaseModel):
    prompt_text: str | None = None
    text_to_show: str | None = None
    audio_blob_path: str | None = None
    image_blob_path: str | None = None
    language_code: str = "es-PE"
    expected_text: str


class CreateExerciseRequest(BaseModel):
    type: ExerciseType
    title: str = Field(min_length=1, max_length=255)
    instructions: str | None = None
    stimulus_type: str | None = None
    response_type: str | None = None
    difficulty_level: int | None = Field(default=None, ge=1, le=5)
    mc_question: MCQuestionData | None = None
    os_question: OSQuestionData | None = None
    prompt_exercise: PromptExerciseData | None = None


class ExerciseResponse(BaseModel):
    exercise_id: UUID
    type: str
    title: str
    instructions: str | None
    stimulus_type: str | None
    response_type: str | None
    difficulty_level: int | None
    is_active: bool
    created_by_teacher_id: UUID | None
    created_at: datetime
    updated_at: datetime


class AttachExerciseRequest(BaseModel):
    exercise_id: UUID
    order_index: int
    points: int = 10
    is_required: bool = True


class CreateAssessmentRequest(BaseModel):
    template_id: UUID
    classroom_id: UUID
    title: str | None = None
    scheduled_at: date | None = None


class AssessmentResponse(BaseModel):
    assessment_id: UUID
    template_id: UUID
    classroom_id: UUID
    homeroom_teacher_id: UUID
    title: str | None
    status: str
    scheduled_at: date | None
    created_at: datetime
    updated_at: datetime


class StartAttemptRequest(BaseModel):
    student_id: UUID


class PromptExerciseSchema(BaseModel):
    prompt_text: str | None = None
    text_to_show: str | None = None
    audio_blob_path: str | None = None
    image_blob_path: str | None = None
    language_code: str | None = None


class ExerciseDetail(BaseModel):
    exercise_id: UUID
    type: str
    title: str
    instructions: str | None = None
    stimulus_type: str | None = None
    response_type: str | None = None
    difficulty_level: int | None = None
    order_index: int = 0
    points: int = 0
    is_required: bool = True
    prompt_exercise: PromptExerciseSchema | None = None


class ExerciseAttemptItem(BaseModel):
    exercise_attempt_id: UUID
    template_exercise_id: UUID
    status: str
    started_at: datetime | None
    submitted_at: datetime | None
    exercise: ExerciseDetail | None = None


class AttemptResponse(BaseModel):
    attempt_id: UUID
    assessment_id: UUID
    student_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    exercise_attempts: list[ExerciseAttemptItem] = []


class AttemptDetailResponse(BaseModel):
    attempt_id: UUID
    assessment_id: UUID
    student_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    exercise_attempts: list[ExerciseAttemptItem]


class SubmitMCResponseRequest(BaseModel):
    selected_option_id: UUID


class MCResponseResponse(BaseModel):
    response_id: UUID
    exercise_attempt_id: UUID
    selected_option_id: UUID
    is_correct: bool | None


class SubmitOSResponseRequest(BaseModel):
    selected_syllables: list[str]
    formed_word: str | None = None


class OSResponseResponse(BaseModel):
    response_id: UUID
    exercise_attempt_id: UUID
    selected_syllables: list[str]
    formed_word: str | None
    is_correct: bool | None


class SpeakingResponseResponse(BaseModel):
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


class WritingResponseResponse(BaseModel):
    response_id: UUID
    exercise_attempt_id: UUID
    image_blob_path: str
    original_filename: str | None
    content_type: str | None


class AssessmentResultResponse(BaseModel):
    attempt_id: UUID
    final_score: float | None
    max_score: float | None
    mc_correct_count: int | None
    os_correct_count: int | None
    speaking_completed_count: int | None
    writing_completed_count: int | None
    intervention_level: str | None
    generated_at: datetime | None
    speaking_average_score: float | None = None
    speaking_review_required_count: int = 0
    total_exercises: int = 0
    evaluated_exercises: int = 0
    pending_exercises: int = 0


class AttemptListItem(BaseModel):
    attempt_id: UUID
    assessment_id: UUID
    student_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    final_score: float | None = None
    intervention_level: str | None = None


class AttemptListResponse(BaseModel):
    items: list[AttemptListItem]
    total: int


class DownloadUrlResponse(BaseModel):
    download_url: str


class PronunciationWordResponse(BaseModel):
    word: str | None
    accuracy_score: float | None
    error_type: str | None
    offset: int | None
    duration: int | None
    phonemes: list[dict]


class PronunciationScoresResponse(BaseModel):
    accuracy_score: float | None
    fluency_score: float | None
    completeness_score: float | None
    pronunciation_score: float | None
    prosody_score: float | None
    prosody_supported: bool
    words: list[PronunciationWordResponse]


class PronunciationAssessmentResponse(BaseModel):
    status: str
    stt_status: str
    pronunciation_status: str
    expected_text: str | None
    recognized_text: str | None
    stt_recognized_text: str | None
    assessment_recognized_text: str | None
    assessment_display_text: str | None
    assessment_lexical_text: str | None
    stt: dict
    locale: str | None
    pronunciation_assessment: dict
    comparison: dict | None
    review: dict
    diagnostics: dict
    error: dict | None
    language_code: str | None
    duration_ms: int | None
    error_message: str | None
    pronunciation_score: float | None
    accuracy_score: float | None
    fluency_score: float | None
    completeness_score: float | None
    prosody_score: float | None
    missing_fields: list[str]
    azure_config_used: dict | None = None
    raw_result_json: dict | None = None
