from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
import json
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
from app.assessment.infrastructure.adapters.azure_vision_ocr import (
    AzureVisionOcrAdapter,
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
    SQLAlchemyExpectedAnswerRepository,
    SQLAlchemyOSQuestionRepository,
    SQLAlchemyOSResponseRepository,
    SQLAlchemyPromptExerciseRepository,
    SQLAlchemySpeakingMetricsRepository,
    SQLAlchemySpeakingResponseRepository,
    SQLAlchemyTemplateExerciseRepository,
    SQLAlchemyTemplateRepository,
    SQLAlchemyWritingMetricsRepository,
    SQLAlchemyWritingResponseRepository,
)
from app.assessment.domain.enums import ExerciseType
from app.assessment.domain.question import MCQuestion
from app.assessment.domain.metrics import AssessmentResult as AssessmentResultDomain
from app.assessment.domain.writing_text_comparison import char_accuracy, word_accuracy
from app.assessment.presentation.schemas import (
    AssessmentResponse,
    AssessmentResultResponse,
    AttemptDetailResponse,
    AttemptListResponse,
    AttemptListItem,
    AttemptResponse,
    AttachExerciseRequest,
    CreateAssessmentRequest,
    CreateExerciseRequest,
    CreateTemplateRequest,
    DownloadUrlResponse,
    ExerciseAttemptItem,
    ExerciseResponse,
    MCQuestionImageUploadResponse,
    MCResponseResponse,
    OSResponseResponse,
    PronunciationAssessmentResponse,
    SpeakingResponseResponse,
    StartAttemptRequest,
    SubmitMCResponseRequest,
    SubmitOSResponseRequest,
    TemplateResponse,
    WritingMetricsResponse,
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
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}


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


ALLOWED_MC_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_MC_IMAGE_SIZE = 5 * 1024 * 1024


@router.post(
    "/exercises/{exercise_id}/mc-question/image",
    response_model=MCQuestionImageUploadResponse,
    status_code=status.HTTP_200_OK,
)
def upload_mc_question_image(
    exercise_id: UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> MCQuestionImageUploadResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)

    ex_repo = SQLAlchemyExerciseRepository(db)
    exercise = ex_repo.find_by_id(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    if exercise.type != ExerciseType.MULTIPLE_CHOICE:
        raise HTTPException(status_code=400, detail="Exercise is not MULTIPLE_CHOICE")

    mc_q_repo = SQLAlchemyMCQuestionRepository(db)
    mc_q = mc_q_repo.find_by_exercise_id(exercise_id)
    if not mc_q:
        raise HTTPException(status_code=404, detail="MC question not found for this exercise")

    if file.content_type not in ALLOWED_MC_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. Allowed: png, jpg, jpeg, webp",
        )
    content = file.file.read()
    if len(content) > MAX_MC_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image file exceeds 5 MB limit")

    ext = Path(file.filename or "image.png").suffix or ".png"
    blob_path = f"assessment-assets/exercises/{exercise_id}/mc/question-image{ext}"

    storage = AzureAssessmentBlobStorage(get_settings())
    storage.upload_asset(content=content, content_type=file.content_type, blob_path=blob_path)

    from datetime import UTC, datetime, timezone
    now = datetime.now(timezone.utc)
    updated = mc_q_repo.update(
        MCQuestion(
            id=mc_q.id,
            exercise_id=mc_q.exercise_id,
            question_text=mc_q.question_text,
            image_blob_path=blob_path,
            created_at=mc_q.created_at,
            updated_at=now,
        )
    )

    db.commit()
    return MCQuestionImageUploadResponse(
        exercise_id=exercise_id,
        mc_question_id=updated.id,
        image_blob_path=blob_path,
        content_type=file.content_type,
        size_bytes=len(content),
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


@router.get("/{assessment_id}/attempts", response_model=AttemptListResponse)
def list_attempts(
    assessment_id: UUID,
    student_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AttemptListResponse:
    _resolve_teacher_id(db, current_user.id)
    attempt_repo = SQLAlchemyAssessmentAttemptRepository(db)
    attempts = attempt_repo.find_by_assessment_id(assessment_id)

    if student_id:
        attempts = [a for a in attempts if a.student_id == student_id]
    if status:
        attempts = [a for a in attempts if a.status.value == status]

    total = len(attempts)
    paginated = attempts[offset:offset + limit]

    result_ids = [a.id for a in paginated]
    results_map: dict[UUID, AssessmentResultDomain] = {}
    if result_ids:
        result_repo = SQLAlchemyAssessmentResultRepository(db)
        for rid in result_ids:
            r = result_repo.find_by_attempt_id(rid)
            if r:
                results_map[rid] = r

    items = []
    for a in paginated:
        r = results_map.get(a.id)
        items.append(
            AttemptListItem(
                attempt_id=a.id,
                assessment_id=a.assessment_id,
                student_id=a.student_id,
                status=a.status.value,
                started_at=a.started_at,
                completed_at=a.completed_at,
                final_score=r.final_score if r else None,
                intervention_level=r.intervention_level.value if r and r.intervention_level else None,
            )
        )
    return AttemptListResponse(items=items, total=total)


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
        exercise_attempts=[
            ExerciseAttemptItem(
                exercise_attempt_id=ea.exercise_attempt_id,
                template_exercise_id=ea.template_exercise_id,
                status=ea.status.value,
                started_at=ea.started_at,
                submitted_at=ea.submitted_at,
            )
            for ea in (result.exercise_attempts or [])
        ],
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
    te_repo = SQLAlchemyTemplateExerciseRepository(db)
    ex_repo = SQLAlchemyExerciseRepository(db)
    prompt_repo = SQLAlchemyPromptExerciseRepository(db)
    mc_q_repo = SQLAlchemyMCQuestionRepository(db)
    mc_opt_repo = SQLAlchemyMCAnswerOptionRepository(db)
    os_q_repo = SQLAlchemyOSQuestionRepository(db)
    os_a_repo = SQLAlchemyOSAnswerRepository(db)
    exercise_attempt_items = []
    for ea in exercise_attempts:
        te = te_repo.find_by_id(ea.template_exercise_id)
        exercise_detail = None
        if te:
            exercise = ex_repo.find_by_id(te.exercise_id)
            if exercise:
                prompt = prompt_repo.find_by_exercise_id(exercise.id) if exercise.type in (
                    ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING,
                    ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING,
                ) else None
                from app.assessment.presentation.schemas import (
                    PromptExerciseSchema, ExerciseDetail,
                    MCOptionSchema, MCQuestionSchema, OSQuestionSchema,
                )
                mc_question = None
                os_question = None
                if exercise.type == ExerciseType.MULTIPLE_CHOICE:
                    mc_q = mc_q_repo.find_by_exercise_id(exercise.id)
                    if mc_q:
                        options = mc_opt_repo.find_by_question_id(mc_q.id)
                        image_url = None
                        if mc_q.image_blob_path:
                            try:
                                storage = AzureAssessmentBlobStorage(get_settings())
                                image_url = storage.download_url(blob_path=mc_q.image_blob_path)
                            except Exception:
                                pass
                        mc_question = MCQuestionSchema(
                            question_text=mc_q.question_text,
                            image_blob_path=mc_q.image_blob_path,
                            image_url=image_url,
                            options=[
                                MCOptionSchema(
                                    option_id=opt.id,
                                    text=opt.text,
                                    order_index=opt.order_index,
                                )
                                for opt in options
                            ],
                        )
                elif exercise.type == ExerciseType.ORDER_SYLLABLES:
                    os_q = os_q_repo.find_by_exercise_id(exercise.id)
                    if os_q:
                        os_a = os_a_repo.find_by_question_id(os_q.id)
                        os_question = OSQuestionSchema(
                            question_text=os_q.question_text,
                            image_blob_path=os_q.image_blob_path,
                            syllables_json=os_a.syllables_json if os_a else [],
                        )
                exercise_detail = ExerciseDetail(
                    exercise_id=exercise.id,
                    type=exercise.type.value,
                    title=exercise.title,
                    instructions=exercise.instructions,
                    stimulus_type=exercise.stimulus_type,
                    response_type=exercise.response_type,
                    difficulty_level=exercise.difficulty_level,
                    order_index=te.order_index,
                    points=te.points,
                    is_required=te.is_required,
                    prompt_exercise=PromptExerciseSchema(
                        prompt_text=prompt.prompt_text,
                        text_to_show=prompt.text_to_show,
                        audio_blob_path=prompt.audio_blob_path,
                        image_blob_path=prompt.image_blob_path,
                        language_code=prompt.language_code,
                    ) if prompt else None,
                    mc_question=mc_question,
                    os_question=os_question,
                )
        exercise_attempt_items.append(
            ExerciseAttemptItem(
                exercise_attempt_id=ea.id,
                template_exercise_id=ea.template_exercise_id,
                status=ea.status.value,
                started_at=ea.started_at,
                submitted_at=ea.submitted_at,
                exercise=exercise_detail,
            )
        )
    return AttemptDetailResponse(
        attempt_id=attempt.id,
        assessment_id=attempt.assessment_id,
        student_id=attempt.student_id,
        status=attempt.status.value,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        exercise_attempts=exercise_attempt_items,
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


@router.get(
    "/exercise-attempts/{exercise_attempt_id}/speaking-response",
    response_model=SpeakingResponseResponse,
)
def get_speaking_response(
    exercise_attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> SpeakingResponseResponse:
    _resolve_teacher_id(db, current_user.id)
    speaking_repo = SQLAlchemySpeakingResponseRepository(db)
    metrics_repo = SQLAlchemySpeakingMetricsRepository(db)

    speaking_resp = speaking_repo.find_by_exercise_attempt_id(exercise_attempt_id)
    if not speaking_resp:
        raise HTTPException(status_code=404, detail="Speaking response not found")

    metrics = metrics_repo.find_by_speaking_response_id(speaking_resp.id)

    evaluation_status = "completed"
    if not metrics and not speaking_resp.free_transcription_text:
        evaluation_status = "failed"
    elif not metrics:
        evaluation_status = "partial"
    raw_json = metrics.raw_speech_result_json if metrics else None
    comparison = raw_json.get("comparison") if raw_json else None
    review = raw_json.get("review") if raw_json else None

    return SpeakingResponseResponse(
        response_id=speaking_resp.id,
        exercise_attempt_id=speaking_resp.exercise_attempt_id,
        audio_blob_path=speaking_resp.audio_blob_path,
        original_filename=speaking_resp.original_filename,
        content_type=speaking_resp.content_type,
        duration_ms=speaking_resp.duration_ms,
        free_transcription_text=speaking_resp.free_transcription_text,
        assessment_recognized_text=speaking_resp.assessment_recognized_text,
        recognized_text=speaking_resp.recognized_text,
        pronunciation_score=metrics.pronunciation_score if metrics else None,
        accuracy_score=metrics.accuracy_score if metrics else None,
        fluency_score=metrics.fluency_score if metrics else None,
        completeness_score=metrics.completeness_score if metrics else None,
        prosody_score=metrics.prosody_score if metrics else None,
        evaluation_status=evaluation_status,
        comparison=comparison,
        review=review,
        error_message=None,
    )


@router.post(
    "/exercise-attempts/{exercise_attempt_id}/writing-response",
    response_model=WritingResponseResponse,
)
def upload_writing_response(
    exercise_attempt_id: UUID,
    file: UploadFile,
    payload_json: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> WritingResponseResponse:
    _resolve_teacher_id(db, current_user.id)

    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. Allowed: png, jpg, jpeg, webp",
        )
    content = file.file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image file exceeds 10 MB limit")

    parsed_payload: dict | None = None
    if payload_json:
        try:
            parsed_payload = json.loads(payload_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="payload_json must be valid JSON.")

    settings = get_settings()
    ocr_service = (
        AzureVisionOcrAdapter(settings)
        if settings.azure_vision_endpoint and settings.azure_vision_key
        else None
    )
    uc = UploadWritingResponseUseCase(
        exercise_attempt_repo=SQLAlchemyExerciseAttemptRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
        exercise_repo=SQLAlchemyExerciseRepository(db),
        assessment_attempt_repo=SQLAlchemyAssessmentAttemptRepository(db),
        assessment_repo=SQLAlchemyAssessmentRepository(db),
        writing_response_repo=SQLAlchemyWritingResponseRepository(db),
        writing_metrics_repo=SQLAlchemyWritingMetricsRepository(db),
        blob_storage=AzureAssessmentBlobStorage(settings),
        ocr_service=ocr_service,
        prompt_exercise_repo=SQLAlchemyPromptExerciseRepository(db),
        expected_answer_repo=SQLAlchemyExpectedAnswerRepository(db),
    )
    try:
        result = uc.execute(
            UploadWritingResponseCommand(
                exercise_attempt_id=exercise_attempt_id,
                file_content=content,
                original_filename=file.filename or "image.png",
                content_type=file.content_type or "image/png",
                payload_json=parsed_payload,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()

    image_url = None
    try:
        image_url = AzureAssessmentBlobStorage(get_settings()).download_url(
            blob_path=result.image_blob_path
        )
    except Exception:
        pass

    metrics_response = None
    try:
        metrics_repo = SQLAlchemyWritingMetricsRepository(db)
        metrics = metrics_repo.find_by_writing_response_id(result.response_id)
        if metrics:
            _cer, _wer, _sim = metrics.cer, metrics.wer, metrics.similarity_score
            _c_acc = char_accuracy(_cer) if _cer is not None else None
            _w_acc = word_accuracy(_wer) if _wer is not None else None
            _reasons: list[str] = []
            if metrics.confidence_avg is not None and metrics.confidence_avg < 0.70:
                _reasons.append("LOW_OCR_CONFIDENCE")
            if _sim is not None and _sim < 75:
                _reasons.append("LOW_TEXT_SIMILARITY")
            if _cer is not None and _cer >= 0.25:
                _reasons.append("HIGH_CHARACTER_ERROR_RATE")
            if _wer is not None and _wer >= 0.50 and _c_acc is not None and _c_acc < 85:
                _reasons.append("HIGH_WORD_ERROR_RATE")
            metrics_response = WritingMetricsResponse(
                duration_ms=metrics.duration_ms,
                stroke_count=metrics.stroke_count,
                point_count=metrics.point_count,
                average_speed=metrics.average_speed,
                speed_variability=metrics.speed_variability,
                pause_count=metrics.pause_count,
                longest_pause_ms=metrics.longest_pause_ms,
                total_pause_time_ms=metrics.total_pause_time_ms,
                pressure_min=metrics.pressure_min,
                pressure_max=metrics.pressure_max,
                pressure_avg=metrics.pressure_avg,
                bounding_box=metrics.bounding_box_json,
                writing_area_usage=metrics.writing_area_usage,
                confidence_avg=metrics.confidence_avg,
                raw_ocr_result_json=metrics.raw_ocr_result_json,
                cer=_cer,
                wer=_wer,
                similarity_score=_sim,
                review_required=len(_reasons) > 0,
                review_reasons=_reasons,
                char_accuracy=_c_acc,
                word_accuracy=_w_acc,
            )
    except Exception:
        pass

    return WritingResponseResponse(
        response_id=result.response_id,
        exercise_attempt_id=result.exercise_attempt_id,
        image_blob_path=result.image_blob_path,
        original_filename=result.original_filename,
        content_type=result.content_type,
        recognized_text=result.recognized_text,
        strokes_json=result.strokes_json,
        canvas_metadata=result.canvas_metadata_json,
        input_metadata=result.input_metadata_json,
        frontend_metrics=result.frontend_metrics_json,
        metrics=metrics_response,
        image_url=image_url,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get(
    "/exercise-attempts/{exercise_attempt_id}/writing-response",
    response_model=WritingResponseResponse,
)
def get_writing_response(
    exercise_attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> WritingResponseResponse:
    _resolve_teacher_id(db, current_user.id)
    writing_repo = SQLAlchemyWritingResponseRepository(db)
    metrics_repo = SQLAlchemyWritingMetricsRepository(db)

    writing_resp = writing_repo.find_by_exercise_attempt_id(exercise_attempt_id)
    if not writing_resp:
        raise HTTPException(status_code=404, detail="Writing response not found")

    metrics = metrics_repo.find_by_writing_response_id(writing_resp.id)

    image_url = None
    try:
        image_url = AzureAssessmentBlobStorage(get_settings()).download_url(
            blob_path=writing_resp.image_blob_path
        )
    except Exception:
        pass

    metrics_response = None
    if metrics:
        _cer, _wer, _sim = metrics.cer, metrics.wer, metrics.similarity_score
        _c_acc = char_accuracy(_cer) if _cer is not None else None
        _w_acc = word_accuracy(_wer) if _wer is not None else None
        _reasons: list[str] = []
        if metrics.confidence_avg is not None and metrics.confidence_avg < 0.70:
            _reasons.append("LOW_OCR_CONFIDENCE")
        if _sim is not None and _sim < 75:
            _reasons.append("LOW_TEXT_SIMILARITY")
        if _cer is not None and _cer >= 0.25:
            _reasons.append("HIGH_CHARACTER_ERROR_RATE")
        if _wer is not None and _wer >= 0.50 and _c_acc is not None and _c_acc < 85:
            _reasons.append("HIGH_WORD_ERROR_RATE")
        metrics_response = WritingMetricsResponse(
            duration_ms=metrics.duration_ms,
            stroke_count=metrics.stroke_count,
            point_count=metrics.point_count,
            average_speed=metrics.average_speed,
            speed_variability=metrics.speed_variability,
            pause_count=metrics.pause_count,
            longest_pause_ms=metrics.longest_pause_ms,
            total_pause_time_ms=metrics.total_pause_time_ms,
            pressure_min=metrics.pressure_min,
            pressure_max=metrics.pressure_max,
            pressure_avg=metrics.pressure_avg,
            bounding_box=metrics.bounding_box_json,
            writing_area_usage=metrics.writing_area_usage,
            confidence_avg=metrics.confidence_avg,
            raw_ocr_result_json=metrics.raw_ocr_result_json,
            cer=_cer,
            wer=_wer,
            similarity_score=_sim,
            review_required=len(_reasons) > 0,
            review_reasons=_reasons,
            char_accuracy=_c_acc,
            word_accuracy=_w_acc,
        )

    return WritingResponseResponse(
        response_id=writing_resp.id,
        exercise_attempt_id=writing_resp.exercise_attempt_id,
        image_blob_path=writing_resp.image_blob_path,
        original_filename=writing_resp.original_filename,
        content_type=writing_resp.content_type,
        recognized_text=writing_resp.recognized_text,
        strokes_json=writing_resp.strokes_json,
        canvas_metadata=writing_resp.canvas_metadata_json,
        input_metadata=writing_resp.input_metadata_json,
        frontend_metrics=writing_resp.frontend_metrics_json,
        metrics=metrics_response,
        image_url=image_url,
        created_at=writing_resp.created_at,
        updated_at=writing_resp.updated_at,
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
        writing_metrics_repo=SQLAlchemyWritingMetricsRepository(db),
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
        writing_average_score=result.writing_average_score,
        writing_review_required_count=result.writing_review_required_count,
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
        exercise_attempt_repo=SQLAlchemyExerciseAttemptRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
        exercise_repo=SQLAlchemyExerciseRepository(db),
        mc_response_repo=SQLAlchemyMCResponseRepository(db),
        os_response_repo=SQLAlchemyOSResponseRepository(db),
        speaking_response_repo=SQLAlchemySpeakingResponseRepository(db),
        writing_response_repo=SQLAlchemyWritingResponseRepository(db),
        writing_metrics_repo=SQLAlchemyWritingMetricsRepository(db),
        speaking_metrics_repo=SQLAlchemySpeakingMetricsRepository(db),
        prompt_exercise_repo=SQLAlchemyPromptExerciseRepository(db),
        expected_answer_repo=SQLAlchemyExpectedAnswerRepository(db),
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
        writing_average_score=result.writing_average_score,
        writing_review_required_count=result.writing_review_required_count,
    )


@router.get(
    "/exercise-attempts/{exercise_attempt_id}/mc-response",
    response_model=MCResponseResponse,
)
def get_mc_response(
    exercise_attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> MCResponseResponse:
    _resolve_teacher_id(db, current_user.id)
    repo = SQLAlchemyMCResponseRepository(db)
    response = repo.find_by_exercise_attempt_id(exercise_attempt_id)
    if not response:
        raise HTTPException(status_code=404, detail="MC response not found")
    return MCResponseResponse(
        response_id=response.id,
        exercise_attempt_id=response.exercise_attempt_id,
        selected_option_id=response.selected_option_id,
        is_correct=response.is_correct,
        created_at=response.created_at,
        updated_at=response.updated_at,
    )


@router.get(
    "/exercise-attempts/{exercise_attempt_id}/os-response",
    response_model=OSResponseResponse,
)
def get_os_response(
    exercise_attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> OSResponseResponse:
    _resolve_teacher_id(db, current_user.id)
    repo = SQLAlchemyOSResponseRepository(db)
    response = repo.find_by_exercise_attempt_id(exercise_attempt_id)
    if not response:
        raise HTTPException(status_code=404, detail="OS response not found")
    return OSResponseResponse(
        response_id=response.id,
        exercise_attempt_id=response.exercise_attempt_id,
        selected_syllables=response.selected_syllables_json,
        formed_word=response.formed_word,
        is_correct=response.is_correct,
        created_at=response.created_at,
        updated_at=response.updated_at,
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
