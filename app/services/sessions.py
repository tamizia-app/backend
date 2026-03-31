from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.domain.enums import RiskFlag, SessionStatus
from app.models.assessment_session import AssessmentSession
from app.models.audio_sample import AudioSample
from app.models.ocr_analysis import OCRAnalysis
from app.models.pronunciation_analysis import PronunciationAnalysis
from app.models.session_result import SessionResult
from app.models.student import Student
from app.models.user import User
from app.models.writing_sample import WritingSample
from app.schemas.session import SessionCreate
from app.services.analysis.result_builder import build_observation, build_overall_score, build_risk_flag
from app.services.analysis.text_metrics import (
    build_reading_score,
    build_writing_score,
    cer,
    omission_and_substitution_counts,
    wer,
)
from app.services.audit import create_audit_log
from app.services.auth import require_teacher_profile_id
from app.services.azure.ocr import OCRService
from app.services.azure.speech import PronunciationService
from app.services.azure.storage import ObjectStorageService
from app.services.exercises import get_exercise
from app.services.students import get_student_for_user


def _ensure_session_is_open(session: AssessmentSession) -> None:
    if session.status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is closed for new evidence.")


def create_session(db: Session, *, current_user: User, payload: SessionCreate) -> AssessmentSession:
    student = get_student_for_user(db, payload.student_id, current_user)
    get_exercise(db, payload.exercise_id)
    session = AssessmentSession(
        student_id=student.id,
        exercise_id=payload.exercise_id,
        teacher_profile_id=require_teacher_profile_id(current_user),
        status=SessionStatus.PENDING,
    )
    db.add(session)
    db.flush()
    create_audit_log(db, user=current_user, action="create_session", entity_type="assessment_session", entity_id=session.id)
    return session


def get_session_for_user(db: Session, session_id, current_user: User) -> AssessmentSession:
    query = (
        select(AssessmentSession)
        .where(AssessmentSession.id == session_id)
        .options(
            joinedload(AssessmentSession.writing_sample).joinedload(WritingSample.analysis),
            joinedload(AssessmentSession.audio_sample).joinedload(AudioSample.analysis),
            joinedload(AssessmentSession.result),
        )
    )
    session = db.scalar(query)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    get_student_for_user(db, session.student_id, current_user)
    return session


def list_sessions_by_student(db: Session, *, student_id, current_user: User) -> list[AssessmentSession]:
    student = get_student_for_user(db, student_id, current_user)
    query = select(AssessmentSession).where(AssessmentSession.student_id == student.id).order_by(AssessmentSession.created_at.desc())
    return list(db.scalars(query))


def start_session(db: Session, *, session: AssessmentSession, current_user: User) -> AssessmentSession:
    if session.status not in {SessionStatus.PENDING, SessionStatus.FAILED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session cannot be started from current state.")
    session.status = SessionStatus.IN_PROGRESS
    session.started_at = datetime.now(UTC)
    db.flush()
    create_audit_log(db, user=current_user, action="start_session", entity_type="assessment_session", entity_id=session.id)
    return session


def complete_session(db: Session, *, session: AssessmentSession, current_user: User) -> AssessmentSession:
    if session.status not in {SessionStatus.PENDING, SessionStatus.IN_PROGRESS}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session cannot be completed from current state.")
    completed_at = datetime.now(UTC)
    session.completed_at = completed_at
    session.status = SessionStatus.COMPLETED
    if session.started_at:
        session.duration_seconds = int((completed_at - session.started_at).total_seconds())
    db.flush()
    create_audit_log(db, user=current_user, action="complete_session", entity_type="assessment_session", entity_id=session.id)
    return session


def cancel_session(db: Session, *, session: AssessmentSession, current_user: User) -> AssessmentSession:
    if session.status == SessionStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed sessions cannot be cancelled.")
    session.status = SessionStatus.CANCELLED
    session.completed_at = datetime.now(UTC)
    if session.started_at:
        session.duration_seconds = int((session.completed_at - session.started_at).total_seconds())
    db.flush()
    create_audit_log(db, user=current_user, action="cancel_session", entity_type="assessment_session", entity_id=session.id)
    return session


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
    _ensure_session_is_open(session)
    content = await file.read()
    image_url = storage_service.upload_bytes(
        content=content,
        folder="writing-samples",
        filename=file.filename or "writing.png",
        content_type=file.content_type or "image/png",
    )

    _clear_session_result_and_analysis(db, session=session, sample_type="writing")
    sample = session.writing_sample or WritingSample(session_id=session.id, image_url=image_url, source_type=source_type)
    sample.image_url = image_url
    sample.source_type = source_type
    sample.stroke_count = stroke_count
    sample.correction_count = correction_count
    sample.duration_seconds = duration_seconds
    sample.captured_at = datetime.now(UTC)
    db.add(sample)
    db.flush()
    create_audit_log(db, user=current_user, action="upload_writing_sample", entity_type="writing_sample", entity_id=sample.id)
    return sample


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
    _ensure_session_is_open(session)
    content = await file.read()
    audio_url = storage_service.upload_bytes(
        content=content,
        folder="audio-samples",
        filename=file.filename or "reading.wav",
        content_type=file.content_type or "audio/wav",
    )

    _clear_session_result_and_analysis(db, session=session, sample_type="audio")
    sample = session.audio_sample or AudioSample(session_id=session.id, audio_url=audio_url, locale=locale)
    sample.audio_url = audio_url
    sample.locale = locale
    sample.duration_seconds = duration_seconds
    sample.captured_at = datetime.now(UTC)
    db.add(sample)
    db.flush()
    create_audit_log(db, user=current_user, action="upload_audio_sample", entity_type="audio_sample", entity_id=sample.id)
    return sample


def analyze_writing(
    db: Session,
    *,
    session: AssessmentSession,
    current_user: User,
    ocr_service: OCRService,
) -> tuple[OCRAnalysis, float | None]:
    _ensure_session_is_open(session)
    if not session.writing_sample:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Writing sample is required before analysis.")

    image_bytes = _load_binary_source(session.writing_sample.image_url)
    ocr_result = ocr_service.analyze_image(image_bytes)
    reference_text = session.exercise.reference_text
    cer_score = cer(reference_text, ocr_result.extracted_text)
    wer_score = wer(reference_text, ocr_result.extracted_text)
    omissions, substitutions = omission_and_substitution_counts(reference_text, ocr_result.extracted_text)
    writing_score = build_writing_score(
        cer_score=cer_score,
        wer_score=wer_score,
        omissions=omissions,
        substitutions=substitutions,
    )

    analysis = session.writing_sample.analysis or OCRAnalysis(writing_sample_id=session.writing_sample.id)
    analysis.extracted_text = ocr_result.extracted_text
    analysis.confidence_avg = ocr_result.confidence_avg
    analysis.cer_score = round(cer_score, 4)
    analysis.wer_score = round(wer_score, 4)
    analysis.omissions = omissions
    analysis.substitutions = substitutions
    analysis.raw_response = ocr_result.raw_response
    analysis.analyzed_at = datetime.now(UTC)
    db.add(analysis)
    db.flush()
    create_audit_log(db, user=current_user, action="analyze_writing", entity_type="ocr_analysis", entity_id=analysis.id)
    return analysis, writing_score


def analyze_reading(
    db: Session,
    *,
    session: AssessmentSession,
    current_user: User,
    pronunciation_service: PronunciationService,
) -> tuple[PronunciationAnalysis, float | None]:
    _ensure_session_is_open(session)
    if not session.audio_sample:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Audio sample is required before analysis.")

    audio_bytes = _load_binary_source(session.audio_sample.audio_url)
    pronunciation_result = pronunciation_service.analyze_audio(
        audio_bytes=audio_bytes,
        reference_text=session.exercise.reference_text,
        locale=session.audio_sample.locale,
    )
    reading_score = build_reading_score(
        accuracy_score=pronunciation_result.accuracy_score,
        fluency_score=pronunciation_result.fluency_score,
        completeness_score=pronunciation_result.completeness_score,
        pronunciation_score=pronunciation_result.pronunciation_score,
    )

    analysis = session.audio_sample.analysis or PronunciationAnalysis(audio_sample_id=session.audio_sample.id)
    analysis.accuracy_score = pronunciation_result.accuracy_score
    analysis.fluency_score = pronunciation_result.fluency_score
    analysis.completeness_score = pronunciation_result.completeness_score
    analysis.pronunciation_score = pronunciation_result.pronunciation_score
    analysis.recognized_text = pronunciation_result.recognized_text
    analysis.raw_response = pronunciation_result.raw_response
    analysis.analyzed_at = datetime.now(UTC)
    db.add(analysis)
    db.flush()
    create_audit_log(
        db,
        user=current_user,
        action="analyze_reading",
        entity_type="pronunciation_analysis",
        entity_id=analysis.id,
    )
    return analysis, reading_score


def generate_session_result(db: Session, *, session: AssessmentSession, current_user: User) -> SessionResult:
    writing_score = None
    if session.writing_sample and session.writing_sample.analysis:
        writing_score = build_writing_score(
            cer_score=session.writing_sample.analysis.cer_score,
            wer_score=session.writing_sample.analysis.wer_score,
            omissions=session.writing_sample.analysis.omissions,
            substitutions=session.writing_sample.analysis.substitutions,
        )

    reading_score = None
    if session.audio_sample and session.audio_sample.analysis:
        reading_score = build_reading_score(
            accuracy_score=session.audio_sample.analysis.accuracy_score,
            fluency_score=session.audio_sample.analysis.fluency_score,
            completeness_score=session.audio_sample.analysis.completeness_score,
            pronunciation_score=session.audio_sample.analysis.pronunciation_score,
        )

    overall_score = build_overall_score(writing_score, reading_score)
    if writing_score is None and reading_score is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="At least one completed analysis is required.")
    risk_flag = build_risk_flag(overall_score, writing_score, reading_score)
    observation = build_observation(risk_flag)

    result = session.result or SessionResult(session_id=session.id, observation=observation, risk_flag=RiskFlag.MEDIUM)
    result.writing_score = writing_score
    result.reading_score = reading_score
    result.overall_score = overall_score
    result.risk_flag = risk_flag
    result.observation = observation
    result.generated_at = datetime.now(UTC)
    db.add(result)
    db.flush()
    create_audit_log(db, user=current_user, action="generate_result", entity_type="session_result", entity_id=result.id)
    return result
