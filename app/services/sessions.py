from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile, status
import httpx
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.domain.enums import SessionStatus
from app.models.assessment_session import AssessmentSession
from app.models.ocr_analysis import OCRAnalysis
from app.models.pronunciation_analysis import PronunciationAnalysis
from app.models.session_result import SessionResult
from app.models.user import User
from app.modules.ai_processing.application.process_reading_pronunciation import (
    ProcessReadingPronunciationCommand,
    ProcessReadingPronunciationUseCase,
)
from app.modules.ai_processing.application.process_writing_ocr import ProcessWritingOCRCommand, ProcessWritingOCRUseCase
from app.modules.ai_processing.domain.exceptions import (
    AIProcessingError,
    AudioSampleRequiredError,
    SessionClosedForAnalysisError,
    WritingSampleRequiredError,
)
from app.modules.ai_processing.infrastructure.binary_loader import HTTPOrLocalBinarySourceLoader
from app.modules.ai_processing.infrastructure.repositories import SQLAlchemyAIProcessingRepository
from app.modules.assessment_sessions.application.commands.cancel_session import CancelSessionCommand, CancelSessionUseCase
from app.modules.assessment_sessions.application.commands.complete_session import CompleteSessionCommand, CompleteSessionUseCase
from app.modules.assessment_sessions.application.commands.create_session import CreateSessionCommand, CreateSessionUseCase
from app.modules.assessment_sessions.application.commands.start_session import StartSessionCommand, StartSessionUseCase
from app.modules.assessment_sessions.application.queries.get_session import (
    GetSessionQuery,
    GetSessionUseCase,
    ListSessionsByStudentQuery,
    ListSessionsByStudentUseCase,
)
from app.modules.assessment_sessions.domain.exceptions import (
    AssessmentSessionError,
    ExerciseNotFoundError,
    InvalidSessionStateError,
    SessionNotBelongsToTeacherError,
    SessionNotFoundError,
    StudentNotBelongsToTeacherError,
    StudentNotFoundError,
    TeacherProfileMissingError,
)
from app.modules.assessment_sessions.infrastructure.repositories import SQLAlchemyAssessmentSessionRepository
from app.modules.evidences.application.upload_audio_evidence import UploadAudioEvidenceCommand, UploadAudioEvidenceUseCase
from app.modules.evidences.application.upload_writing_evidence import UploadWritingEvidenceCommand, UploadWritingEvidenceUseCase
from app.modules.evidences.domain.entities import AudioEvidenceMetadata, EvidenceFile, WritingEvidenceMetadata
from app.modules.evidences.domain.exceptions import EvidenceError, SessionClosedForEvidenceError
from app.modules.evidences.infrastructure.repositories import SQLAlchemyEvidenceRepository
from app.modules.results.application.generate_result import GenerateResultCommand, GenerateResultUseCase
from app.modules.results.domain.exceptions import AnalysisRequiredError, ResultError
from app.modules.results.infrastructure.repositories import SQLAlchemyResultRepository
from app.schemas.session import SessionCreate
from app.services.azure.ocr import OCRService
from app.services.azure.speech import PronunciationService
from app.services.azure.storage import ObjectStorageService


def _ensure_session_is_open(session: AssessmentSession) -> None:
    if session.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is closed for new evidence.")


def _raise_session_http_error(
    error: AssessmentSessionError,
    *,
    invalid_state_detail: str = "Session cannot transition from current state.",
) -> None:
    if isinstance(error, TeacherProfileMissingError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher profile not configured.") from error
    if isinstance(error, ExerciseNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found.") from error
    if isinstance(error, (StudentNotFoundError, StudentNotBelongsToTeacherError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.") from error
    if isinstance(error, (SessionNotFoundError, SessionNotBelongsToTeacherError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from error
    if isinstance(error, InvalidSessionStateError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=invalid_state_detail) from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session operation failed.") from error


def create_session(db: Session, *, current_user: User, payload: SessionCreate) -> AssessmentSession:
    try:
        return CreateSessionUseCase(SQLAlchemyAssessmentSessionRepository(db)).execute(
            CreateSessionCommand(
                student_id=payload.student_id,
                exercise_id=payload.exercise_id,
                current_user=current_user,
            )
        )
    except AssessmentSessionError as error:
        _raise_session_http_error(error)


def get_session_for_user(db: Session, session_id, current_user: User) -> AssessmentSession:
    try:
        return GetSessionUseCase(SQLAlchemyAssessmentSessionRepository(db)).execute(
            GetSessionQuery(session_id=session_id, current_user=current_user)
        )
    except AssessmentSessionError as error:
        _raise_session_http_error(error)


def list_sessions_by_student(db: Session, *, student_id, current_user: User) -> list[AssessmentSession]:
    try:
        return ListSessionsByStudentUseCase(SQLAlchemyAssessmentSessionRepository(db)).execute(
            ListSessionsByStudentQuery(student_id=student_id, current_user=current_user)
        )
    except AssessmentSessionError as error:
        _raise_session_http_error(error)


def start_session(db: Session, *, session: AssessmentSession, current_user: User) -> AssessmentSession:
    try:
        return StartSessionUseCase(SQLAlchemyAssessmentSessionRepository(db)).execute(
            StartSessionCommand(session_id=session.id, current_user=current_user)
        )
    except AssessmentSessionError as error:
        _raise_session_http_error(error, invalid_state_detail="Session cannot be started from current state.")


def complete_session(db: Session, *, session: AssessmentSession, current_user: User) -> AssessmentSession:
    try:
        return CompleteSessionUseCase(SQLAlchemyAssessmentSessionRepository(db)).execute(
            CompleteSessionCommand(session_id=session.id, current_user=current_user)
        )
    except AssessmentSessionError as error:
        _raise_session_http_error(error, invalid_state_detail="Session cannot be completed from current state.")


def cancel_session(db: Session, *, session: AssessmentSession, current_user: User) -> AssessmentSession:
    try:
        return CancelSessionUseCase(SQLAlchemyAssessmentSessionRepository(db)).execute(
            CancelSessionCommand(session_id=session.id, current_user=current_user)
        )
    except AssessmentSessionError as error:
        _raise_session_http_error(error, invalid_state_detail="Completed sessions cannot be cancelled.")


def _clear_session_result_and_analysis(db: Session, *, session: AssessmentSession, sample_type: str) -> None:
    if sample_type == "writing" and session.writing_sample:
        db.execute(delete(OCRAnalysis).where(OCRAnalysis.writing_sample_id == session.writing_sample.id))
    if sample_type == "audio" and session.audio_sample:
        db.execute(delete(PronunciationAnalysis).where(PronunciationAnalysis.audio_sample_id == session.audio_sample.id))
    db.execute(delete(SessionResult).where(SessionResult.session_id == session.id))
    db.flush()


def _load_binary_source(location: str) -> bytes:
    if location.startswith("http://") or location.startswith("https://"):
        response = httpx.get(location, timeout=60.0)
        response.raise_for_status()
        return response.content
    return Path(location).read_bytes()


async def save_writing_sample(
    db: Session,
    *,
    session: AssessmentSession,
    current_user: User,
    storage_service: ObjectStorageService,
    file: UploadFile,
    source_type: str,
    stroke_count: int | None,
    correction_count: int | None,
    duration_seconds: int | None,
) -> WritingSample:
    content = await file.read()
    try:
        return UploadWritingEvidenceUseCase(SQLAlchemyEvidenceRepository(db), storage_service).execute(
            UploadWritingEvidenceCommand(
                session=session,
                current_user=current_user,
                file=EvidenceFile(
                    content=content,
                    filename=file.filename or "writing.png",
                    content_type=file.content_type or "image/png",
                ),
                metadata=WritingEvidenceMetadata(
                    source_type=source_type,
                    stroke_count=stroke_count,
                    correction_count=correction_count,
                    duration_seconds=duration_seconds,
                ),
            )
        )
    except SessionClosedForEvidenceError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is closed for new evidence.") from error
    except EvidenceError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evidence operation failed.") from error


async def save_audio_sample(
    db: Session,
    *,
    session: AssessmentSession,
    current_user: User,
    storage_service: ObjectStorageService,
    file: UploadFile,
    locale: str,
    duration_seconds: int | None,
) -> AudioSample:
    content = await file.read()
    try:
        return UploadAudioEvidenceUseCase(SQLAlchemyEvidenceRepository(db), storage_service).execute(
            UploadAudioEvidenceCommand(
                session=session,
                current_user=current_user,
                file=EvidenceFile(
                    content=content,
                    filename=file.filename or "reading.wav",
                    content_type=file.content_type or "audio/wav",
                ),
                metadata=AudioEvidenceMetadata(locale=locale, duration_seconds=duration_seconds),
            )
        )
    except SessionClosedForEvidenceError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is closed for new evidence.") from error
    except EvidenceError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evidence operation failed.") from error


def analyze_writing(
    db: Session,
    *,
    session: AssessmentSession,
    current_user: User,
    ocr_service: OCRService,
) -> tuple[OCRAnalysis, float | None]:
    try:
        return ProcessWritingOCRUseCase(
            repository=SQLAlchemyAIProcessingRepository(db),
            binary_loader=HTTPOrLocalBinarySourceLoader(),
            ocr_processor=ocr_service,
        ).execute(ProcessWritingOCRCommand(session=session, current_user=current_user))
    except SessionClosedForAnalysisError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is closed for new evidence.") from error
    except WritingSampleRequiredError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Writing sample is required before analysis.") from error
    except AIProcessingError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI processing operation failed.") from error


def analyze_reading(
    db: Session,
    *,
    session: AssessmentSession,
    current_user: User,
    pronunciation_service: PronunciationService,
) -> tuple[PronunciationAnalysis, float | None]:
    try:
        return ProcessReadingPronunciationUseCase(
            repository=SQLAlchemyAIProcessingRepository(db),
            binary_loader=HTTPOrLocalBinarySourceLoader(),
            pronunciation_processor=pronunciation_service,
        ).execute(ProcessReadingPronunciationCommand(session=session, current_user=current_user))
    except SessionClosedForAnalysisError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is closed for new evidence.") from error
    except AudioSampleRequiredError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Audio sample is required before analysis.") from error
    except AIProcessingError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI processing operation failed.") from error


def generate_session_result(db: Session, *, session: AssessmentSession, current_user: User) -> SessionResult:
    try:
        return GenerateResultUseCase(SQLAlchemyResultRepository(db)).execute(
            GenerateResultCommand(session=session, current_user=current_user)
        )
    except AnalysisRequiredError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="At least one completed analysis is required.") from error
    except ResultError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Result operation failed.") from error
