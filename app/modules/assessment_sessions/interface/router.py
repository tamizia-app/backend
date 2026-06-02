from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_ocr_service, get_pronunciation_service, get_storage_service
from app.models.user import User
from app.modules.assessment_sessions.application.commands.cancel_session import CancelSessionCommand, CancelSessionUseCase
from app.modules.assessment_sessions.application.commands.complete_session import CompleteSessionCommand, CompleteSessionUseCase
from app.modules.assessment_sessions.application.commands.create_session import CreateSessionCommand, CreateSessionUseCase
from app.modules.assessment_sessions.application.commands.start_session import StartSessionCommand, StartSessionUseCase
from app.modules.assessment_sessions.application.queries.get_session import GetSessionQuery, GetSessionUseCase
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
from app.modules.assessment_sessions.interface.schemas import (
    AudioSampleResponse,
    GenerateResultResponse,
    ReadingAnalyzeResponse,
    SessionCreate,
    SessionDetailResponse,
    SessionResponse,
    SessionResultResponse,
    SessionUpdateStateResponse,
    WritingAnalyzeResponse,
    WritingSampleResponse,
)
from app.modules.ai_processing.application.process_reading_pronunciation import (
    ProcessReadingPronunciationCommand,
    ProcessReadingPronunciationUseCase,
)
from app.modules.ai_processing.application.process_writing_ocr import ProcessWritingOCRCommand, ProcessWritingOCRUseCase
from app.modules.ai_processing.domain.exceptions import AIProcessingError
from app.modules.ai_processing.infrastructure.binary_loader import HTTPOrLocalBinarySourceLoader
from app.modules.ai_processing.infrastructure.ocr import OCRService
from app.modules.ai_processing.infrastructure.repositories import SQLAlchemyAIProcessingRepository
from app.modules.ai_processing.infrastructure.speech import PronunciationService
from app.modules.ai_processing.interface.router_helpers import raise_ai_processing_http_error
from app.modules.evidences.application.upload_audio_evidence import UploadAudioEvidenceCommand, UploadAudioEvidenceUseCase
from app.modules.evidences.application.upload_writing_evidence import UploadWritingEvidenceCommand, UploadWritingEvidenceUseCase
from app.modules.evidences.domain.entities import AudioEvidenceMetadata, WritingEvidenceMetadata
from app.modules.evidences.domain.exceptions import EvidenceError
from app.modules.evidences.infrastructure.repositories import SQLAlchemyEvidenceRepository
from app.modules.evidences.interface.router_helpers import evidence_file_from_upload, raise_evidence_http_error
from app.modules.evidences.infrastructure.storage import ObjectStorageService
from app.modules.results.application.generate_result import GenerateResultCommand, GenerateResultUseCase
from app.modules.results.application.get_result import GetResultBySessionQuery, GetResultBySessionUseCase
from app.modules.results.domain.exceptions import ResultError
from app.modules.results.infrastructure.repositories import SQLAlchemyResultRepository
from app.modules.results.interface.router_helpers import raise_result_http_error


router = APIRouter(prefix="/sessions")


def get_session_repository(db: Session = Depends(get_db)) -> SQLAlchemyAssessmentSessionRepository:
    return SQLAlchemyAssessmentSessionRepository(db)


def _raise_http_error(error: AssessmentSessionError, *, invalid_state_detail: str = "Session cannot transition from current state.") -> None:
    if isinstance(error, TeacherProfileMissingError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher profile not configured.",
        ) from error
    if isinstance(error, ExerciseNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found.") from error
    if isinstance(error, (StudentNotFoundError, StudentNotBelongsToTeacherError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.") from error
    if isinstance(error, (SessionNotFoundError, SessionNotBelongsToTeacherError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.") from error
    if isinstance(error, InvalidSessionStateError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=invalid_state_detail) from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session operation failed.") from error


def _build_session_detail(session) -> SessionDetailResponse:
    return SessionDetailResponse(
        **SessionResponse.model_validate(session).model_dump(),
        writing_sample=session.writing_sample,
        audio_sample=session.audio_sample,
        ocr_analysis=session.writing_sample.analysis if session.writing_sample else None,
        pronunciation_analysis=session.audio_sample.analysis if session.audio_sample else None,
        result=session.result,
    )


def _get_session_or_http(repository: SQLAlchemyAssessmentSessionRepository, *, session_id: UUID, current_user: User):
    try:
        return GetSessionUseCase(repository).execute(GetSessionQuery(session_id=session_id, current_user=current_user))
    except AssessmentSessionError as error:
        _raise_http_error(error)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    repository = SQLAlchemyAssessmentSessionRepository(db)
    try:
        session = CreateSessionUseCase(repository).execute(
            CreateSessionCommand(
                student_id=payload.student_id,
                exercise_id=payload.exercise_id,
                current_user=current_user,
            )
        )
    except AssessmentSessionError as error:
        _raise_http_error(error)

    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: UUID,
    repository: SQLAlchemyAssessmentSessionRepository = Depends(get_session_repository),
    current_user: User = Depends(get_current_user),
) -> SessionDetailResponse:
    session = _get_session_or_http(repository, session_id=session_id, current_user=current_user)
    return _build_session_detail(session)


@router.patch("/{session_id}/start", response_model=SessionUpdateStateResponse)
def start_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionUpdateStateResponse:
    repository = SQLAlchemyAssessmentSessionRepository(db)
    try:
        session = StartSessionUseCase(repository).execute(StartSessionCommand(session_id=session_id, current_user=current_user))
    except AssessmentSessionError as error:
        _raise_http_error(error, invalid_state_detail="Session cannot be started from current state.")
    db.commit()
    return session


@router.patch("/{session_id}/complete", response_model=SessionUpdateStateResponse)
def complete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionUpdateStateResponse:
    repository = SQLAlchemyAssessmentSessionRepository(db)
    try:
        session = CompleteSessionUseCase(repository).execute(
            CompleteSessionCommand(session_id=session_id, current_user=current_user)
        )
    except AssessmentSessionError as error:
        _raise_http_error(error, invalid_state_detail="Session cannot be completed from current state.")
    db.commit()
    return session


@router.patch("/{session_id}/cancel", response_model=SessionUpdateStateResponse)
def cancel_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionUpdateStateResponse:
    repository = SQLAlchemyAssessmentSessionRepository(db)
    try:
        session = CancelSessionUseCase(repository).execute(CancelSessionCommand(session_id=session_id, current_user=current_user))
    except AssessmentSessionError as error:
        _raise_http_error(error, invalid_state_detail="Completed sessions cannot be cancelled.")
    db.commit()
    return session


@router.post("/{session_id}/writing-sample", response_model=WritingSampleResponse, status_code=status.HTTP_201_CREATED)
async def upload_writing_sample(
    session_id: UUID,
    file: UploadFile = File(...),
    source_type: str = Form(...),
    stroke_count: int | None = Form(default=None),
    correction_count: int | None = Form(default=None),
    duration_seconds: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_service: ObjectStorageService = Depends(get_storage_service),
) -> WritingSampleResponse:
    session = _get_session_or_http(SQLAlchemyAssessmentSessionRepository(db), session_id=session_id, current_user=current_user)
    evidence_file = await evidence_file_from_upload(file, default_filename="writing.png", default_content_type="image/png")
    try:
        sample = UploadWritingEvidenceUseCase(SQLAlchemyEvidenceRepository(db), storage_service).execute(
            UploadWritingEvidenceCommand(
                session=session,
                current_user=current_user,
                file=evidence_file,
                metadata=WritingEvidenceMetadata(
                    source_type=source_type,
                    stroke_count=stroke_count,
                    correction_count=correction_count,
                    duration_seconds=duration_seconds,
                ),
            )
        )
    except EvidenceError as error:
        raise_evidence_http_error(error)
    db.commit()
    db.refresh(sample)
    return sample


@router.post("/{session_id}/audio-sample", response_model=AudioSampleResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio_sample(
    session_id: UUID,
    file: UploadFile = File(...),
    locale: str = Form(default="es-CO"),
    duration_seconds: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage_service: ObjectStorageService = Depends(get_storage_service),
) -> AudioSampleResponse:
    session = _get_session_or_http(SQLAlchemyAssessmentSessionRepository(db), session_id=session_id, current_user=current_user)
    evidence_file = await evidence_file_from_upload(file, default_filename="reading.wav", default_content_type="audio/wav")
    try:
        sample = UploadAudioEvidenceUseCase(SQLAlchemyEvidenceRepository(db), storage_service).execute(
            UploadAudioEvidenceCommand(
                session=session,
                current_user=current_user,
                file=evidence_file,
                metadata=AudioEvidenceMetadata(locale=locale, duration_seconds=duration_seconds),
            )
        )
    except EvidenceError as error:
        raise_evidence_http_error(error)
    db.commit()
    db.refresh(sample)
    return sample


@router.post("/{session_id}/analyze-writing", response_model=WritingAnalyzeResponse)
def analyze_writing(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
) -> WritingAnalyzeResponse:
    session = _get_session_or_http(SQLAlchemyAssessmentSessionRepository(db), session_id=session_id, current_user=current_user)
    try:
        analysis, writing_score = ProcessWritingOCRUseCase(
            repository=SQLAlchemyAIProcessingRepository(db),
            binary_loader=HTTPOrLocalBinarySourceLoader(),
            ocr_processor=ocr_service,
        ).execute(ProcessWritingOCRCommand(session=session, current_user=current_user))
    except AIProcessingError as error:
        raise_ai_processing_http_error(error)
    db.commit()
    db.refresh(analysis)
    return WritingAnalyzeResponse(analysis=analysis, writing_score=writing_score)


@router.post("/{session_id}/analyze-reading", response_model=ReadingAnalyzeResponse)
def analyze_reading(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pronunciation_service: PronunciationService = Depends(get_pronunciation_service),
) -> ReadingAnalyzeResponse:
    session = _get_session_or_http(SQLAlchemyAssessmentSessionRepository(db), session_id=session_id, current_user=current_user)
    try:
        analysis, reading_score = ProcessReadingPronunciationUseCase(
            repository=SQLAlchemyAIProcessingRepository(db),
            binary_loader=HTTPOrLocalBinarySourceLoader(),
            pronunciation_processor=pronunciation_service,
        ).execute(ProcessReadingPronunciationCommand(session=session, current_user=current_user))
    except AIProcessingError as error:
        raise_ai_processing_http_error(error)
    db.commit()
    db.refresh(analysis)
    return ReadingAnalyzeResponse(analysis=analysis, reading_score=reading_score)


@router.post("/{session_id}/generate-result", response_model=GenerateResultResponse)
def generate_result(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateResultResponse:
    session = _get_session_or_http(SQLAlchemyAssessmentSessionRepository(db), session_id=session_id, current_user=current_user)
    try:
        result = GenerateResultUseCase(SQLAlchemyResultRepository(db)).execute(
            GenerateResultCommand(session=session, current_user=current_user)
        )
    except ResultError as error:
        raise_result_http_error(error)
    db.commit()
    db.refresh(result)
    return GenerateResultResponse(result=result)


@router.get("/{session_id}/result", response_model=SessionResultResponse)
def get_result(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResultResponse:
    session = _get_session_or_http(SQLAlchemyAssessmentSessionRepository(db), session_id=session_id, current_user=current_user)
    try:
        return GetResultBySessionUseCase(SQLAlchemyResultRepository(db)).execute(
            GetResultBySessionQuery(session_id=session.id, current_user=current_user)
        )
    except ResultError as error:
        raise_result_http_error(error)
