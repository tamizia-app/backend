from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_ocr_service, get_pronunciation_service, get_storage_service
from app.models.user import User
from app.schemas.session import (
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
from app.services import sessions as session_service
from app.services.azure.ocr import OCRService
from app.services.azure.speech import PronunciationService
from app.services.azure.storage import ObjectStorageService


router = APIRouter(prefix="/sessions")


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    session = session_service.create_session(db, current_user=current_user, payload=payload)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> SessionDetailResponse:
    session = session_service.get_session_for_user(db, session_id, current_user)
    return SessionDetailResponse(
        **SessionResponse.model_validate(session).model_dump(),
        writing_sample=session.writing_sample,
        audio_sample=session.audio_sample,
        ocr_analysis=session.writing_sample.analysis if session.writing_sample else None,
        pronunciation_analysis=session.audio_sample.analysis if session.audio_sample else None,
        result=session.result,
    )


@router.patch("/{session_id}/start", response_model=SessionUpdateStateResponse)
def start_session(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> SessionUpdateStateResponse:
    session = session_service.get_session_for_user(db, session_id, current_user)
    session = session_service.start_session(db, session=session, current_user=current_user)
    db.commit()
    return session


@router.patch("/{session_id}/complete", response_model=SessionUpdateStateResponse)
def complete_session(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> SessionUpdateStateResponse:
    session = session_service.get_session_for_user(db, session_id, current_user)
    session = session_service.complete_session(db, session=session, current_user=current_user)
    db.commit()
    return session


@router.patch("/{session_id}/cancel", response_model=SessionUpdateStateResponse)
def cancel_session(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> SessionUpdateStateResponse:
    session = session_service.get_session_for_user(db, session_id, current_user)
    session = session_service.cancel_session(db, session=session, current_user=current_user)
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
    session = session_service.get_session_for_user(db, session_id, current_user)
    sample = await session_service.save_writing_sample(
        db,
        session=session,
        current_user=current_user,
        storage_service=storage_service,
        file=file,
        source_type=source_type,
        stroke_count=stroke_count,
        correction_count=correction_count,
        duration_seconds=duration_seconds,
    )
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
    session = session_service.get_session_for_user(db, session_id, current_user)
    sample = await session_service.save_audio_sample(
        db,
        session=session,
        current_user=current_user,
        storage_service=storage_service,
        file=file,
        locale=locale,
        duration_seconds=duration_seconds,
    )
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
    session = session_service.get_session_for_user(db, session_id, current_user)
    analysis, writing_score = session_service.analyze_writing(
        db,
        session=session,
        current_user=current_user,
        ocr_service=ocr_service,
    )
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
    session = session_service.get_session_for_user(db, session_id, current_user)
    analysis, reading_score = session_service.analyze_reading(
        db,
        session=session,
        current_user=current_user,
        pronunciation_service=pronunciation_service,
    )
    db.commit()
    db.refresh(analysis)
    return ReadingAnalyzeResponse(analysis=analysis, reading_score=reading_score)


@router.post("/{session_id}/generate-result", response_model=GenerateResultResponse)
def generate_result(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateResultResponse:
    session = session_service.get_session_for_user(db, session_id, current_user)
    result = session_service.generate_session_result(db, session=session, current_user=current_user)
    db.commit()
    db.refresh(result)
    return GenerateResultResponse(result=result)


@router.get("/{session_id}/result", response_model=SessionResultResponse)
def get_result(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> SessionResultResponse:
    session = session_service.get_session_for_user(db, session_id, current_user)
    if not session.result:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found.")
    return session.result

