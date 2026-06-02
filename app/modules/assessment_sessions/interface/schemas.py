from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import RiskFlag, SessionStatus
from app.schemas.common import ORMModel, TimestampedModel


class SessionCreate(BaseModel):
    student_id: UUID
    exercise_id: UUID


class SessionResponse(TimestampedModel):
    student_id: UUID
    exercise_id: UUID
    teacher_profile_id: UUID
    status: SessionStatus
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: int | None


class SessionUpdateStateResponse(BaseModel):
    id: UUID
    status: SessionStatus
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: int | None


class WritingSampleResponse(ORMModel):
    id: UUID
    session_id: UUID
    image_url: str
    source_type: str
    stroke_count: int | None
    correction_count: int | None
    duration_seconds: int | None
    captured_at: datetime


class AudioSampleResponse(ORMModel):
    id: UUID
    session_id: UUID
    audio_url: str
    duration_seconds: int | None
    locale: str
    captured_at: datetime


class OCRAnalysisResponse(ORMModel):
    id: UUID
    writing_sample_id: UUID
    extracted_text: str
    confidence_avg: float | None
    cer_score: float | None
    wer_score: float | None
    omissions: int | None
    substitutions: int | None
    raw_response: dict | None
    analyzed_at: datetime


class PronunciationAnalysisResponse(ORMModel):
    id: UUID
    audio_sample_id: UUID
    accuracy_score: float | None
    fluency_score: float | None
    completeness_score: float | None
    pronunciation_score: float | None
    recognized_text: str | None
    raw_response: dict | None
    analyzed_at: datetime


class SessionResultResponse(ORMModel):
    id: UUID
    session_id: UUID
    writing_score: float | None
    reading_score: float | None
    overall_score: float | None
    observation: str
    risk_flag: RiskFlag
    generated_at: datetime


class SessionDetailResponse(SessionResponse):
    writing_sample: WritingSampleResponse | None = None
    audio_sample: AudioSampleResponse | None = None
    ocr_analysis: OCRAnalysisResponse | None = None
    pronunciation_analysis: PronunciationAnalysisResponse | None = None
    result: SessionResultResponse | None = None


class WritingAnalyzeResponse(BaseModel):
    analysis: OCRAnalysisResponse
    writing_score: float | None


class ReadingAnalyzeResponse(BaseModel):
    analysis: PronunciationAnalysisResponse
    reading_score: float | None


class GenerateResultResponse(BaseModel):
    result: SessionResultResponse

