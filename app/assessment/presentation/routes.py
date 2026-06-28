from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.assessment.application.exceptions import AssessmentException
from app.assessment.application.use_cases.assess_reading_pipeline import (
    AssessReadingCommand,
    AssessReadingPipelineUseCase,
)
from app.assessment.application.use_cases.attach_exercise_to_template import (
    AttachExerciseCommand,
    AttachExerciseToTemplateUseCase,
)
from app.assessment.application.use_cases.create_assessment import (
    CreateAssessmentCommand,
    CreateAssessmentUseCase,
)
from app.assessment.application.use_cases.create_exercise import (
    CreateExerciseCommand,
    CreateExerciseUseCase,
)
from app.assessment.application.use_cases.create_template import (
    CreateTemplateCommand,
    CreateTemplateUseCase,
)
from app.assessment.application.use_cases.finish_assessment_attempt import (
    FinishAssessmentAttemptCommand,
    FinishAssessmentAttemptUseCase,
)
from app.assessment.application.use_cases.get_assessment_result import (
    GetAssessmentResultQuery,
    GetAssessmentResultUseCase,
)
from app.assessment.application.use_cases.start_assessment_attempt import (
    StartAssessmentAttemptCommand,
    StartAssessmentAttemptUseCase,
)
from app.assessment.application.use_cases.submit_mc_response import (
    SubmitMCResponseCommand,
    SubmitMCResponseUseCase,
)
from app.assessment.application.use_cases.submit_os_response import (
    SubmitOSResponseCommand,
    SubmitOSResponseUseCase,
)
from app.assessment.application.use_cases.upload_speaking_response import (
    UploadSpeakingResponseCommand,
    UploadSpeakingResponseUseCase,
)
from app.assessment.application.use_cases.upload_writing_response import (
    UploadWritingResponseCommand,
    UploadWritingResponseUseCase,
)
from app.assessment.infrastructure.adapters.assessment_blob_storage import (
    AzureAssessmentBlobStorage,
)
from app.assessment.infrastructure.adapters.azure_speech import (
    AzureSpeechPronunciationAssessmentService,
)
from app.assessment.infrastructure.adapters.faster_whisper_stt import (
    FasterWhisperSpeechToTextAdapter,
    WhisperConfig,
)
from app.assessment.infrastructure.audio_processing import (
    AssessmentAudioProcessor,
    AudioProcessingError,
)
from app.assessment.infrastructure.repositories.assessment_repositories import (
    SQLAlchemyAssessmentAttemptRepository,
    SQLAlchemyAssessmentRepository,
    SQLAlchemyAssessmentResultRepository,
    SQLAlchemyExerciseAttemptRepository,
    SQLAlchemyExerciseRepository,
    SQLAlchemyExpectedAnswerRepository,
    SQLAlchemyMCAnswerOptionRepository,
    SQLAlchemyMCQuestionRepository,
    SQLAlchemyMCResponseRepository,
    SQLAlchemyOSAnswerRepository,
    SQLAlchemyOSQuestionRepository,
    SQLAlchemyOSResponseRepository,
    SQLAlchemyPromptExerciseRepository,
    SQLAlchemySpeakingMetricsRepository,
    SQLAlchemySpeakingResponseRepository,
    SQLAlchemyTemplateExerciseRepository,
    SQLAlchemyTemplateRepository,
    SQLAlchemyWritingResponseRepository,
)
from app.assessment.presentation.schemas import (
    AssessmentResponse,
    AssessmentResultResponse,
    AttemptDetailResponse,
    AttemptResponse,
    AttachExerciseRequest,
    CreateAssessmentRequest,
    CreateExerciseRequest,
    CreateTemplateRequest,
    DownloadUrlResponse,
    ExerciseAttemptItem,
    ExerciseResponse,
    MCResponseResponse,
    OSResponseResponse,
    PronunciationAssessmentResponse,
    SpeakingResponseResponse,
    StartAttemptRequest,
    SubmitMCResponseRequest,
    SubmitOSResponseRequest,
    TemplateResponse,
    WritingResponseResponse,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.iam.infrastructure.models.user_model import UserModel
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
from app.school.infrastructure.models.student_model import Student as StudentORM
from app.school.infrastructure.models.student_model import StudentConsent as StudentConsentORM
from app.school.infrastructure.repositories.classroom_repository import SQLAlchemyClassroomRepository
from app.school.infrastructure.repositories.student_repository import (
    SQLAlchemyStudentConsentRepository,
    SQLAlchemyStudentRepository,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _resolve_teacher_id(db: Session, user_id: str) -> UUID:
    teacher = db.query(HomeroomTeacherModel).filter(HomeroomTeacherModel.user_id == user_id).first()
    if not teacher:
        raise HTTPException(status_code=400, detail="Teacher profile not found")
    return teacher.id


def _get_teacher_id_or_none(db: Session, user_id: str) -> UUID | None:
    teacher = db.query(HomeroomTeacherModel).filter(HomeroomTeacherModel.user_id == user_id).first()
    return teacher.id if teacher else None


MAX_AUDIO_SIZE = 20 * 1024 * 1024
MAX_IMAGE_SIZE = 10 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a", "audio/webm", "audio/ogg"}
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}


# ─── Template endpoints ───────────────────────────────────────


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> TemplateResponse:
    teacher_id = _get_teacher_id_or_none(db, current_user.id)
    uc = CreateTemplateUseCase(SQLAlchemyTemplateRepository(db))
    try:
        result = uc.execute(
            CreateTemplateCommand(
                name=request.name,
                description=request.description,
                version=request.version,
                created_by_teacher_id=teacher_id,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return TemplateResponse(
        template_id=result.template_id,
        name=result.name,
        description=result.description,
        version=result.version,
        is_active=result.is_active,
        created_by_teacher_id=result.created_by_teacher_id,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get("/templates", response_model=list[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[TemplateResponse]:
    teacher_id = _get_teacher_id_or_none(db, current_user.id)
    repo = SQLAlchemyTemplateRepository(db)
    templates = repo.find_by_teacher_id(teacher_id) if teacher_id else []
    return [
        TemplateResponse(
            template_id=t.id,
            name=t.name,
            description=t.description,
            version=t.version,
            is_active=t.is_active,
            created_by_teacher_id=t.created_by_teacher_id,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in templates
    ]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> TemplateResponse:
    repo = SQLAlchemyTemplateRepository(db)
    template = repo.find_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateResponse(
        template_id=template.id,
        name=template.name,
        description=template.description,
        version=template.version,
        is_active=template.is_active,
        created_by_teacher_id=template.created_by_teacher_id,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


# ─── Exercise endpoints ───────────────────────────────────────


@router.post("/exercises", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
def create_exercise(
    request: CreateExerciseRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ExerciseResponse:
    teacher_id = _get_teacher_id_or_none(db, current_user.id)
    uc = CreateExerciseUseCase(
        exercise_repo=SQLAlchemyExerciseRepository(db),
        mc_question_repo=SQLAlchemyMCQuestionRepository(db),
        mc_option_repo=SQLAlchemyMCAnswerOptionRepository(db),
        os_question_repo=SQLAlchemyOSQuestionRepository(db),
        os_answer_repo=SQLAlchemyOSAnswerRepository(db),
        prompt_exercise_repo=SQLAlchemyPromptExerciseRepository(db),
        expected_answer_repo=SQLAlchemyExpectedAnswerRepository(db),
    )
    try:
        result = uc.execute(
            CreateExerciseCommand(
                type=request.type,
                title=request.title,
                instructions=request.instructions,
                stimulus_type=request.stimulus_type,
                response_type=request.response_type,
                difficulty_level=request.difficulty_level,
                created_by_teacher_id=teacher_id,
                mc_question=request.mc_question,
                os_question=request.os_question,
                prompt_exercise=request.prompt_exercise,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return ExerciseResponse(
        exercise_id=result.exercise_id,
        type=result.type.value,
        title=result.title,
        instructions=result.instructions,
        stimulus_type=result.stimulus_type,
        response_type=result.response_type,
        difficulty_level=result.difficulty_level,
        is_active=result.is_active,
        created_by_teacher_id=result.created_by_teacher_id,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(
    exercise_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ExerciseResponse:
    repo = SQLAlchemyExerciseRepository(db)
    exercise = repo.find_by_id(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return ExerciseResponse(
        exercise_id=exercise.id,
        type=exercise.type.value,
        title=exercise.title,
        instructions=exercise.instructions,
        stimulus_type=exercise.stimulus_type,
        response_type=exercise.response_type,
        difficulty_level=exercise.difficulty_level,
        is_active=exercise.is_active,
        created_by_teacher_id=exercise.created_by_teacher_id,
        created_at=exercise.created_at,
        updated_at=exercise.updated_at,
    )


# ─── Template-Exercise attachment ─────────────────────────────


@router.post(
    "/templates/{template_id}/exercises",
    status_code=status.HTTP_201_CREATED,
)
def attach_exercise_to_template(
    template_id: UUID,
    request: AttachExerciseRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    uc = AttachExerciseToTemplateUseCase(
        template_repo=SQLAlchemyTemplateRepository(db),
        exercise_repo=SQLAlchemyExerciseRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
    )
    try:
        uc.execute(
            AttachExerciseCommand(
                template_id=template_id,
                exercise_id=request.exercise_id,
                order_index=request.order_index,
                points=request.points,
                is_required=request.is_required,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return {"detail": "Exercise attached to template successfully."}


# ─── Assessment endpoints ─────────────────────────────────────


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(
    request: CreateAssessmentRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AssessmentResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)
    uc = CreateAssessmentUseCase(
        assessment_repo=SQLAlchemyAssessmentRepository(db),
        template_repo=SQLAlchemyTemplateRepository(db),
        classroom_repo=SQLAlchemyClassroomRepository(db),
    )
    try:
        result = uc.execute(
            CreateAssessmentCommand(
                template_id=request.template_id,
                classroom_id=request.classroom_id,
                homeroom_teacher_id=teacher_id,
                title=request.title,
                scheduled_at=request.scheduled_at,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return AssessmentResponse(
        assessment_id=result.assessment_id,
        template_id=result.template_id,
        classroom_id=result.classroom_id,
        homeroom_teacher_id=result.homeroom_teacher_id,
        title=result.title,
        status=result.status.value,
        scheduled_at=result.scheduled_at,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get("", response_model=list[AssessmentResponse])
def list_assessments(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[AssessmentResponse]:
    teacher_id = _resolve_teacher_id(db, current_user.id)
    repo = SQLAlchemyAssessmentRepository(db)
    assessments = repo.find_by_teacher_id(teacher_id)
    return [
        AssessmentResponse(
            assessment_id=a.id,
            template_id=a.template_id,
            classroom_id=a.classroom_id,
            homeroom_teacher_id=a.homeroom_teacher_id,
            title=a.title,
            status=a.status.value,
            scheduled_at=a.scheduled_at,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in assessments
    ]


@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AssessmentResponse:
    repo = SQLAlchemyAssessmentRepository(db)
    assessment = repo.find_by_id(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return AssessmentResponse(
        assessment_id=assessment.id,
        template_id=assessment.template_id,
        classroom_id=assessment.classroom_id,
        homeroom_teacher_id=assessment.homeroom_teacher_id,
        title=assessment.title,
        status=assessment.status.value,
        scheduled_at=assessment.scheduled_at,
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
    )


# ─── Attempt endpoints ────────────────────────────────────────


@router.post(
    "/{assessment_id}/attempts",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_attempt(
    assessment_id: UUID,
    request: StartAttemptRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AttemptResponse:
    _resolve_teacher_id(db, current_user.id)
    uc = StartAssessmentAttemptUseCase(
        assessment_repo=SQLAlchemyAssessmentRepository(db),
        attempt_repo=SQLAlchemyAssessmentAttemptRepository(db),
        exercise_attempt_repo=SQLAlchemyExerciseAttemptRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
        template_repo=SQLAlchemyTemplateRepository(db),
        student_repo=SQLAlchemyStudentRepository(db),
        consent_repo=SQLAlchemyStudentConsentRepository(db),
    )
    try:
        result = uc.execute(
            StartAssessmentAttemptCommand(
                assessment_id=assessment_id,
                student_id=request.student_id,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return AttemptResponse(
        attempt_id=result.attempt_id,
        assessment_id=result.assessment_id,
        student_id=result.student_id,
        status=result.status.value,
        started_at=result.started_at,
        completed_at=result.completed_at,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get("/attempts/{attempt_id}")
def get_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AttemptDetailResponse:
    _resolve_teacher_id(db, current_user.id)
    attempt_repo = SQLAlchemyAssessmentAttemptRepository(db)
    ea_repo = SQLAlchemyExerciseAttemptRepository(db)
    attempt = attempt_repo.find_by_id(attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    exercise_attempts = ea_repo.find_by_assessment_attempt_id(attempt_id)
    return AttemptDetailResponse(
        attempt_id=attempt.id,
        assessment_id=attempt.assessment_id,
        student_id=attempt.student_id,
        status=attempt.status.value,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        exercise_attempts=[
            ExerciseAttemptItem(
                exercise_attempt_id=ea.id,
                template_exercise_id=ea.template_exercise_id,
                status=ea.status.value,
                started_at=ea.started_at,
                submitted_at=ea.submitted_at,
            )
            for ea in exercise_attempts
        ],
    )


@router.post(
    "/exercise-attempts/{exercise_attempt_id}/mc-response",
    response_model=MCResponseResponse,
)
def submit_mc_response(
    exercise_attempt_id: UUID,
    request: SubmitMCResponseRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> MCResponseResponse:
    _resolve_teacher_id(db, current_user.id)
    uc = SubmitMCResponseUseCase(
        exercise_attempt_repo=SQLAlchemyExerciseAttemptRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
        exercise_repo=SQLAlchemyExerciseRepository(db),
        mc_response_repo=SQLAlchemyMCResponseRepository(db),
        mc_option_repo=SQLAlchemyMCAnswerOptionRepository(db),
    )
    try:
        result = uc.execute(
            SubmitMCResponseCommand(
                exercise_attempt_id=exercise_attempt_id,
                selected_option_id=request.selected_option_id,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return MCResponseResponse(
        response_id=result.response_id,
        exercise_attempt_id=result.exercise_attempt_id,
        selected_option_id=result.selected_option_id,
        is_correct=result.is_correct,
    )


@router.post(
    "/exercise-attempts/{exercise_attempt_id}/os-response",
    response_model=OSResponseResponse,
)
def submit_os_response(
    exercise_attempt_id: UUID,
    request: SubmitOSResponseRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> OSResponseResponse:
    _resolve_teacher_id(db, current_user.id)
    uc = SubmitOSResponseUseCase(
        exercise_attempt_repo=SQLAlchemyExerciseAttemptRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
        exercise_repo=SQLAlchemyExerciseRepository(db),
        os_response_repo=SQLAlchemyOSResponseRepository(db),
        os_question_repo=SQLAlchemyOSQuestionRepository(db),
        os_answer_repo=SQLAlchemyOSAnswerRepository(db),
    )
    try:
        result = uc.execute(
            SubmitOSResponseCommand(
                exercise_attempt_id=exercise_attempt_id,
                selected_syllables=request.selected_syllables,
                formed_word=request.formed_word,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return OSResponseResponse(
        response_id=result.response_id,
        exercise_attempt_id=result.exercise_attempt_id,
        selected_syllables=result.selected_syllables,
        formed_word=result.formed_word,
        is_correct=result.is_correct,
    )


@router.post(
    "/exercise-attempts/{exercise_attempt_id}/speaking-response",
    response_model=SpeakingResponseResponse,
)
async def upload_speaking_response(
    exercise_attempt_id: UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> SpeakingResponseResponse:
    _resolve_teacher_id(db, current_user.id)

    if file.content_type and file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail="Invalid audio format. Allowed: wav, mp3, m4a, webm, ogg")
    content = file.file.read()
    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=400, detail="Audio file exceeds 20 MB limit")

    settings = get_settings()
    whisper_config = WhisperConfig.from_settings(settings)
    pipeline = AssessReadingPipelineUseCase(
        audio_processor=AssessmentAudioProcessor(),
        stt_service=FasterWhisperSpeechToTextAdapter(whisper_config),
        pronunciation_service=AzureSpeechPronunciationAssessmentService(settings),
        low_logprob_threshold=whisper_config.low_confidence_threshold,
    )

    uc = UploadSpeakingResponseUseCase(
        exercise_attempt_repo=SQLAlchemyExerciseAttemptRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
        exercise_repo=SQLAlchemyExerciseRepository(db),
        assessment_attempt_repo=SQLAlchemyAssessmentAttemptRepository(db),
        assessment_repo=SQLAlchemyAssessmentRepository(db),
        speaking_response_repo=SQLAlchemySpeakingResponseRepository(db),
        speaking_metrics_repo=SQLAlchemySpeakingMetricsRepository(db),
        prompt_exercise_repo=SQLAlchemyPromptExerciseRepository(db),
        expected_answer_repo=SQLAlchemyExpectedAnswerRepository(db),
        blob_storage=AzureAssessmentBlobStorage(settings),
        pipeline=pipeline,
    )
    try:
        result = await uc.execute(
            UploadSpeakingResponseCommand(
                exercise_attempt_id=exercise_attempt_id,
                file_content=content,
                original_filename=file.filename or "audio.bin",
                content_type=file.content_type or "audio/wav",
                duration_ms=None,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return SpeakingResponseResponse(
        response_id=result.response_id,
        exercise_attempt_id=result.exercise_attempt_id,
        audio_blob_path=result.audio_blob_path,
        original_filename=result.original_filename,
        content_type=result.content_type,
        duration_ms=result.duration_ms,
        free_transcription_text=result.free_transcription_text,
        assessment_recognized_text=result.assessment_recognized_text,
        recognized_text=result.recognized_text,
        pronunciation_score=result.pronunciation_score,
        accuracy_score=result.accuracy_score,
        fluency_score=result.fluency_score,
        completeness_score=result.completeness_score,
        prosody_score=result.prosody_score,
        evaluation_status=result.evaluation_status,
        comparison=result.comparison,
        review=result.review,
        error_message=result.error_message,
    )


@router.post(
    "/exercise-attempts/{exercise_attempt_id}/writing-response",
    response_model=WritingResponseResponse,
)
def upload_writing_response(
    exercise_attempt_id: UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> WritingResponseResponse:
    _resolve_teacher_id(db, current_user.id)

    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image format. Allowed: png, jpg, jpeg")
    content = file.file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image file exceeds 10 MB limit")

    uc = UploadWritingResponseUseCase(
        exercise_attempt_repo=SQLAlchemyExerciseAttemptRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
        exercise_repo=SQLAlchemyExerciseRepository(db),
        assessment_attempt_repo=SQLAlchemyAssessmentAttemptRepository(db),
        assessment_repo=SQLAlchemyAssessmentRepository(db),
        writing_response_repo=SQLAlchemyWritingResponseRepository(db),
        blob_storage=AzureAssessmentBlobStorage(get_settings()),
    )
    try:
        result = uc.execute(
            UploadWritingResponseCommand(
                exercise_attempt_id=exercise_attempt_id,
                file_content=content,
                original_filename=file.filename or "image.png",
                content_type=file.content_type or "image/png",
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return WritingResponseResponse(
        response_id=result.response_id,
        exercise_attempt_id=result.exercise_attempt_id,
        image_blob_path=result.image_blob_path,
        original_filename=result.original_filename,
        content_type=result.content_type,
    )


@router.post("/attempts/{attempt_id}/finish", response_model=AssessmentResultResponse)
def finish_attempt(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AssessmentResultResponse:
    _resolve_teacher_id(db, current_user.id)
    uc = FinishAssessmentAttemptUseCase(
        attempt_repo=SQLAlchemyAssessmentAttemptRepository(db),
        exercise_attempt_repo=SQLAlchemyExerciseAttemptRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
        exercise_repo=SQLAlchemyExerciseRepository(db),
        mc_response_repo=SQLAlchemyMCResponseRepository(db),
        os_response_repo=SQLAlchemyOSResponseRepository(db),
        speaking_response_repo=SQLAlchemySpeakingResponseRepository(db),
        writing_response_repo=SQLAlchemyWritingResponseRepository(db),
        speaking_metrics_repo=SQLAlchemySpeakingMetricsRepository(db),
        prompt_exercise_repo=SQLAlchemyPromptExerciseRepository(db),
        expected_answer_repo=SQLAlchemyExpectedAnswerRepository(db),
        result_repo=SQLAlchemyAssessmentResultRepository(db),
    )
    try:
        result = uc.execute(FinishAssessmentAttemptCommand(attempt_id=attempt_id))
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return AssessmentResultResponse(
        attempt_id=result.assessment_attempt_id,
        final_score=result.final_score,
        max_score=result.max_score,
        mc_correct_count=result.mc_correct_count,
        os_correct_count=result.os_correct_count,
        speaking_completed_count=result.speaking_completed_count,
        writing_completed_count=result.writing_completed_count,
        intervention_level=result.intervention_level.value if result.intervention_level else None,
        generated_at=result.generated_at,
        speaking_average_score=result.speaking_average_score,
        speaking_review_required_count=result.speaking_review_required_count,
        total_exercises=result.total_exercises,
        evaluated_exercises=result.evaluated_exercises,
        pending_exercises=result.pending_exercises,
    )


@router.get("/attempts/{attempt_id}/result", response_model=AssessmentResultResponse)
def get_result(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AssessmentResultResponse:
    _resolve_teacher_id(db, current_user.id)
    uc = GetAssessmentResultUseCase(
        attempt_repo=SQLAlchemyAssessmentAttemptRepository(db),
        result_repo=SQLAlchemyAssessmentResultRepository(db),
    )
    try:
        result = uc.execute(GetAssessmentResultQuery(attempt_id=attempt_id))
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return AssessmentResultResponse(
        attempt_id=result.attempt_id,
        final_score=result.final_score,
        max_score=result.max_score,
        mc_correct_count=result.mc_correct_count,
        os_correct_count=result.os_correct_count,
        speaking_completed_count=result.speaking_completed_count,
        writing_completed_count=result.writing_completed_count,
        intervention_level=result.intervention_level.value if result.intervention_level else None,
        generated_at=result.generated_at,
        speaking_average_score=result.speaking_average_score,
        speaking_review_required_count=result.speaking_review_required_count,
        total_exercises=result.total_exercises,
        evaluated_exercises=result.evaluated_exercises,
        pending_exercises=result.pending_exercises,
    )


@router.get("/responses/{exercise_attempt_id}/download-url", response_model=DownloadUrlResponse)
def get_response_download_url(
    exercise_attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> DownloadUrlResponse:
    _resolve_teacher_id(db, current_user.id)
    storage = AzureAssessmentBlobStorage(get_settings())

    speaking_repo = SQLAlchemySpeakingResponseRepository(db)
    speaking = speaking_repo.find_by_exercise_attempt_id(exercise_attempt_id)
    if speaking:
        url = storage.download_url(blob_path=speaking.audio_blob_path)
        return DownloadUrlResponse(download_url=url)

    writing_repo = SQLAlchemyWritingResponseRepository(db)
    writing = writing_repo.find_by_exercise_attempt_id(exercise_attempt_id)
    if writing:
        url = storage.download_url(blob_path=writing.image_blob_path)
        return DownloadUrlResponse(download_url=url)

    raise HTTPException(status_code=404, detail="Response not found or no file associated")


# ─── Dev-only Speech Pronunciation Assessment endpoints ────────


def _reject_if_production() -> None:
    settings = get_settings()
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production environment")


@router.post(
    "/dev/speech/pronunciation-assessment",
    response_model=PronunciationAssessmentResponse,
)
async def dev_pronunciation_assessment(
    file: UploadFile,
    reference_text: str = Form(...),
    language_code: str | None = Form(None),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    _reject_if_production()

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file")

    if not reference_text.strip():
        raise HTTPException(status_code=422, detail="Expected text must not be empty")
    try:
        whisper_config = WhisperConfig.from_settings(get_settings())
        pipeline = AssessReadingPipelineUseCase(
            audio_processor=AssessmentAudioProcessor(),
            stt_service=FasterWhisperSpeechToTextAdapter(whisper_config),
            pronunciation_service=AzureSpeechPronunciationAssessmentService(
                get_settings()
            ),
            low_logprob_threshold=whisper_config.low_confidence_threshold,
        )
        response = await pipeline.execute(
            AssessReadingCommand(
                audio_content=content,
                expected_text=reference_text,
                assessment_locale=language_code,
                audio_format=file.content_type or file.filename,
            )
        )
    except (AudioProcessingError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response["azure_config_used"] = {
        "region": get_settings().azure_speech_region,
        "key_configured": bool(get_settings().azure_speech_key),
    }
    return response


@router.post("/dev/speech/compare-languages")
def dev_compare_languages(
    file: UploadFile,
    reference_text: str = Form(...),
    language_codes: str = Form("es-PE,es-ES,es-MX"),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    _reject_if_production()

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file")

    languages = [lang.strip() for lang in language_codes.split(",") if lang.strip()]
    service = AzureSpeechPronunciationAssessmentService(get_settings())

    results = {}
    for lang in languages:
        result = service.assess_pronunciation(
            audio_content=content,
            reference_text=reference_text,
            language_code=lang,
            audio_format=file.content_type or file.filename,
        )
        results[lang] = result.to_dict(include_raw=True)

    return {
        "expected_text": reference_text,
        "reference_text": reference_text,
        "audio_filename": file.filename,
        "results": results,
        "azure_config_used": {
            "region": get_settings().azure_speech_region,
            "key_configured": bool(get_settings().azure_speech_key),
        },
    }
