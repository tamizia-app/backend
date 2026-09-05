from datetime import datetime
from pathlib import Path
from typing import Any
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
from app.assessment.application.use_cases.delete_template import (
    DeleteTemplateCommand,
    DeleteTemplateUseCase,
)
from app.assessment.application.use_cases.finish_assessment_attempt import (
    FinishAssessmentAttemptCommand,
    FinishAssessmentAttemptUseCase,
)
from app.assessment.application.use_cases.get_assessment_result import (
    GetAssessmentResultQuery,
    GetAssessmentResultUseCase,
)
from app.assessment.application.use_cases.get_student_assessment_history import (
    GetStudentAssessmentHistoryQuery,
    GetStudentAssessmentHistoryUseCase,
)
from app.assessment.application.use_cases.list_invalid_template_points import (
    ListInvalidTemplatePointsQuery,
    ListInvalidTemplatePointsUseCase,
)
from app.assessment.application.use_cases.repeat_assessment_attempt import (
    RepeatAssessmentAttemptCommand,
    RepeatAssessmentAttemptUseCase,
)
from app.assessment.application.use_cases.set_template_active import (
    SetTemplateActiveCommand,
    SetTemplateActiveUseCase,
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
from app.assessment.application.use_cases.update_template_exercise_points import (
    UpdateTemplateExercisePointsCommand,
    UpdateTemplateExercisePointsUseCase,
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
    SQLAlchemyExerciseScoreRepository,
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
from app.assessment.domain.technical_quality import SCORING_VERSION_PHASE2_V1
from app.assessment.domain.writing_text_comparison import char_accuracy, word_accuracy
from app.assessment.presentation.schemas import (
    AdminExerciseDetailResponse,
    AdminExerciseListResponse,
    AdminMCQuestionSchema,
    AdminMCOptionSchema,
    AdminOSQuestionSchema,
    AdminPromptExerciseSchema,
    AssessmentResponse,
    AssessmentResultResponse,
    AttemptDetailResponse,
    AttemptListResponse,
    AttemptListItem,
    AttemptResponse,
    AttachExerciseRequest,
    ChartPoint,
    CreateAssessmentRequest,
    CreateExerciseRequest,
    CreateTemplateRequest,
    DownloadUrlResponse,
    ExerciseAttemptItem,
    ExerciseResponse,
    ExerciseReview,
    ExerciseSummary,
    InvalidTemplatePointsResponse,
    MCExpectedReview,
    MCQuestionImageUploadResponse,
    MCResponseResponse,
    MCResponseReview,
    OSExpectedReview,
    OSResponseResponse,
    OSResponseReview,
    PronunciationAssessmentResponse,
    RepeatAttemptRequest,
    RepeatAttemptResponse,
    ReviewResultResponse,
    SpeakingMetricsReview,
    SpeakingResponseResponse,
    SpeakingResponseReview,
    StartAttemptRequest,
    StudentAssessmentHistoryResponse,
    StudentAttemptItem,
    StudentAttemptListResponse,
    StudentInfo,
    SubmitMCResponseRequest,
    SubmitOSResponseRequest,
    TemplateExercisePointsResponse,
    TemplateExercisePointsUpdateRequest,
    TemplateResponse,
    WritingMetricsResponse,
    WritingMetricsReview,
    WritingResponseResponse,
    WritingResponseReview,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.iam.infrastructure.models.user_model import UserModel
from app.school.infrastructure.models.classroom_model import ClassroomModel
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
from app.school.infrastructure.models.student_model import Student as StudentORM
from app.school.infrastructure.models.student_model import StudentConsent as StudentConsentORM
from app.school.infrastructure.repositories.classroom_repository import SQLAlchemyClassroomRepository
from app.school.presentation.schemas import StudentClassroomInfo
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


def _get_student_if_owned_by_teacher(db: Session, student_id: UUID, teacher_id: UUID) -> StudentORM:
    student = db.get(StudentORM, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    classroom = db.get(ClassroomModel, student.classroom_id)
    if not classroom or classroom.homeroom_teacher_id != teacher_id:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


MAX_AUDIO_SIZE = 20 * 1024 * 1024
MAX_IMAGE_SIZE = 10 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a", "audio/webm", "audio/ogg"}
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
PHASE2_FINAL_SCORING_FORMULA = "weighted_mean_by_template_exercise_points"
PHASE2_SCORE_DENOMINATOR_TYPE = "included_weight_sum"


def _phase2_scoring_contract(
    scoring_snapshot: list[dict] | None,
    *,
    score_denominator: int,
    total_exercises: int,
    evaluated_exercises: int,
) -> dict[str, Any]:
    snapshot = scoring_snapshot or []
    meta = next((row for row in snapshot if isinstance(row, dict)), {})

    included_weight_sum = _snapshot_number(
        meta, "included_weight_sum", float(score_denominator or 0)
    )
    total_template_weight_sum = _snapshot_number(
        meta, "total_template_weight_sum", included_weight_sum
    )
    coverage_weight_percentage = _snapshot_number(
        meta,
        "coverage_weight_percentage",
        round((included_weight_sum / total_template_weight_sum) * 100, 2)
        if total_template_weight_sum
        else 0.0,
    )
    included_exercise_count = _snapshot_int(
        meta, "included_exercise_count", evaluated_exercises
    )
    total_exercise_count = _snapshot_int(meta, "total_exercise_count", total_exercises)
    invalid_or_excluded_exercise_count = _snapshot_int(
        meta,
        "invalid_or_excluded_exercise_count",
        max(total_exercise_count - included_exercise_count, 0),
    )

    return {
        "scoring_version": str(meta.get("scoring_version") or SCORING_VERSION_PHASE2_V1),
        "final_scoring_formula": str(
            meta.get("final_scoring_formula") or PHASE2_FINAL_SCORING_FORMULA
        ),
        "included_weight_sum": included_weight_sum,
        "total_template_weight_sum": total_template_weight_sum,
        "coverage_weight_percentage": coverage_weight_percentage,
        "included_exercise_count": included_exercise_count,
        "total_exercise_count": total_exercise_count,
        "invalid_or_excluded_exercise_count": invalid_or_excluded_exercise_count,
        "score_denominator_type": str(
            meta.get("score_denominator_type") or PHASE2_SCORE_DENOMINATOR_TYPE
        ),
        "score_denominator_deprecated": bool(
            meta.get("score_denominator_deprecated", True)
        ),
    }


def _snapshot_number(meta: dict, key: str, fallback: float) -> float:
    value = meta.get(key)
    if isinstance(value, int | float):
        return float(value)
    return float(fallback)


def _snapshot_int(meta: dict, key: str, fallback: int) -> int:
    value = meta.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return int(fallback or 0)


def _template_response(template) -> TemplateResponse:
    return TemplateResponse(
        template_id=template.template_id,
        name=template.name,
        description=template.description,
        version=template.version,
        is_active=template.is_active,
        created_by_teacher_id=template.created_by_teacher_id,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


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


@router.patch("/templates/{template_id}/deactivate", response_model=TemplateResponse)
def deactivate_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> TemplateResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)
    uc = SetTemplateActiveUseCase(SQLAlchemyTemplateRepository(db))
    try:
        result = uc.execute(
            SetTemplateActiveCommand(
                template_id=template_id,
                teacher_id=teacher_id,
                is_active=False,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return _template_response(result)


@router.patch("/templates/{template_id}/activate", response_model=TemplateResponse)
def activate_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> TemplateResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)
    uc = SetTemplateActiveUseCase(SQLAlchemyTemplateRepository(db))
    try:
        result = uc.execute(
            SetTemplateActiveCommand(
                template_id=template_id,
                teacher_id=teacher_id,
                is_active=True,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return _template_response(result)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    teacher_id = _resolve_teacher_id(db, current_user.id)
    uc = DeleteTemplateUseCase(
        template_repo=SQLAlchemyTemplateRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
    )
    try:
        uc.execute(DeleteTemplateCommand(template_id=template_id, teacher_id=teacher_id))
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return None


@router.get(
    "/admin/templates/invalid-points",
    response_model=list[InvalidTemplatePointsResponse],
)
def list_invalid_template_points(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[InvalidTemplatePointsResponse]:
    teacher_id = _resolve_teacher_id(db, current_user.id)
    uc = ListInvalidTemplatePointsUseCase(SQLAlchemyTemplateExerciseRepository(db))
    rows = uc.execute(ListInvalidTemplatePointsQuery(teacher_id=teacher_id))
    return [
        InvalidTemplatePointsResponse(
            template_id=row.template_id,
            template_name=row.template_name,
            template_version=row.template_version,
            is_active=row.is_active,
            template_exercise_id=row.template_exercise_id,
            exercise_id=row.exercise_id,
            exercise_type=row.exercise_type,
            order_index=row.order_index,
            current_points=row.current_points,
            reason=row.reason,
        )
        for row in rows
    ]


@router.patch(
    "/templates/{template_id}/exercises/{template_exercise_id}/points",
    response_model=TemplateExercisePointsResponse,
)
def update_template_exercise_points(
    template_id: UUID,
    template_exercise_id: UUID,
    request: TemplateExercisePointsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> TemplateExercisePointsResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)
    uc = UpdateTemplateExercisePointsUseCase(
        template_repo=SQLAlchemyTemplateRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
    )
    try:
        result = uc.execute(
            UpdateTemplateExercisePointsCommand(
                template_id=template_id,
                template_exercise_id=template_exercise_id,
                teacher_id=teacher_id,
                points=request.points,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return TemplateExercisePointsResponse(
        template_exercise_id=result.id,
        template_id=result.template_id,
        exercise_id=result.exercise_id,
        order_index=result.order_index,
        points=result.points,
        is_required=result.is_required,
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


def _build_admin_exercise_detail(
    exercise, mc_q_repo, mc_opt_repo, os_q_repo, os_a_repo, prompt_repo, expected_repo, db
) -> AdminExerciseDetailResponse:
    mc_question = None
    os_question = None
    prompt_exercise = None

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
            mc_question = AdminMCQuestionSchema(
                mc_question_id=mc_q.id,
                question_text=mc_q.question_text,
                image_blob_path=mc_q.image_blob_path,
                image_url=image_url,
                options=[
                    AdminMCOptionSchema(
                        option_id=opt.id,
                        text=opt.text,
                        is_correct=opt.is_correct,
                        order_index=opt.order_index,
                    )
                    for opt in options
                ],
            )
    elif exercise.type == ExerciseType.ORDER_SYLLABLES:
        os_q = os_q_repo.find_by_exercise_id(exercise.id)
        if os_q:
            os_a = os_a_repo.find_by_question_id(os_q.id)
            os_question = AdminOSQuestionSchema(
                os_question_id=os_q.id,
                question_text=os_q.question_text,
                image_blob_path=os_q.image_blob_path,
                correct_word=os_a.correct_word if os_a else None,
                syllables_json=os_a.syllables_json if os_a else [],
            )
    elif exercise.type in (
        ExerciseType.READING_SPEAKING,
        ExerciseType.LISTENING_SPEAKING,
        ExerciseType.READING_WRITING,
        ExerciseType.LISTENING_WRITING,
    ):
        prompt = prompt_repo.find_by_exercise_id(exercise.id)
        if prompt:
            expected = expected_repo.find_by_prompt_exercise_id(prompt.id)
            prompt_exercise = AdminPromptExerciseSchema(
                prompt_exercise_id=prompt.id,
                prompt_text=prompt.prompt_text,
                text_to_show=prompt.text_to_show,
                audio_blob_path=prompt.audio_blob_path,
                image_blob_path=prompt.image_blob_path,
                language_code=prompt.language_code,
                expected_text=expected.expected_text if expected else None,
            )

    return AdminExerciseDetailResponse(
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
        mc_question=mc_question,
        os_question=os_question,
        prompt_exercise=prompt_exercise,
    )


@router.get("/exercises", response_model=AdminExerciseListResponse)
def list_exercises(
    type: str | None = None,
    difficulty_level: int | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AdminExerciseListResponse:
    repo = SQLAlchemyExerciseRepository(db)
    exercises = repo.find_all(
        type_filter=type,
        difficulty_level=difficulty_level,
        q=q,
        limit=limit,
        offset=offset,
    )
    mc_q_repo = SQLAlchemyMCQuestionRepository(db)
    mc_opt_repo = SQLAlchemyMCAnswerOptionRepository(db)
    os_q_repo = SQLAlchemyOSQuestionRepository(db)
    os_a_repo = SQLAlchemyOSAnswerRepository(db)
    prompt_repo = SQLAlchemyPromptExerciseRepository(db)
    expected_repo = SQLAlchemyExpectedAnswerRepository(db)

    items = [
        _build_admin_exercise_detail(
            ex, mc_q_repo, mc_opt_repo, os_q_repo, os_a_repo, prompt_repo, expected_repo, db
        )
        for ex in exercises
    ]
    return AdminExerciseListResponse(items=items, total=len(items))


@router.get("/exercises/{exercise_id}", response_model=AdminExerciseDetailResponse)
def get_exercise(
    exercise_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AdminExerciseDetailResponse:
    repo = SQLAlchemyExerciseRepository(db)
    exercise = repo.find_by_id(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    mc_q_repo = SQLAlchemyMCQuestionRepository(db)
    mc_opt_repo = SQLAlchemyMCAnswerOptionRepository(db)
    os_q_repo = SQLAlchemyOSQuestionRepository(db)
    os_a_repo = SQLAlchemyOSAnswerRepository(db)
    prompt_repo = SQLAlchemyPromptExerciseRepository(db)
    expected_repo = SQLAlchemyExpectedAnswerRepository(db)
    return _build_admin_exercise_detail(
        exercise, mc_q_repo, mc_opt_repo, os_q_repo, os_a_repo, prompt_repo, expected_repo, db
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
        assessment_attempt_repo=SQLAlchemyAssessmentAttemptRepository(db),
        mc_response_repo=SQLAlchemyMCResponseRepository(db),
        mc_option_repo=SQLAlchemyMCAnswerOptionRepository(db),
        mc_question_repo=SQLAlchemyMCQuestionRepository(db),
        exercise_score_repo=SQLAlchemyExerciseScoreRepository(db),
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
        exercise_score=100.0 if result.is_correct else 0.0,
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
        assessment_attempt_repo=SQLAlchemyAssessmentAttemptRepository(db),
        os_response_repo=SQLAlchemyOSResponseRepository(db),
        os_question_repo=SQLAlchemyOSQuestionRepository(db),
        os_answer_repo=SQLAlchemyOSAnswerRepository(db),
        exercise_score_repo=SQLAlchemyExerciseScoreRepository(db),
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
        exercise_score=100.0 if result.is_correct else 0.0,
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
        exercise_score_repo=SQLAlchemyExerciseScoreRepository(db),
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
        exercise_score=result.exercise_score,
        technical_status=result.technical_status,
        score_eligible=result.score_eligible,
        manual_review_required=result.manual_review_required,
        quality_reasons=result.quality_reasons or [],
        scoring_components=result.scoring_components or {},
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
    score_repo = SQLAlchemyExerciseScoreRepository(db)

    speaking_resp = speaking_repo.find_by_exercise_attempt_id(exercise_attempt_id)
    if not speaking_resp:
        raise HTTPException(status_code=404, detail="Speaking response not found")

    metrics = metrics_repo.find_by_speaking_response_id(speaking_resp.id)

    evaluation_status = "completed"
    if not metrics and not speaking_resp.free_transcription_text:
        evaluation_status = "failed"
    elif not metrics:
        evaluation_status = "partial"
    legacy_raw = metrics.raw_speech_result_json if metrics else None
    comparison = (metrics.comparison_json or (legacy_raw or {}).get("comparison")) if metrics else None
    review = (metrics.review_json or (legacy_raw or {}).get("review")) if metrics else None
    canonical = score_repo.find_by_exercise_attempt_id(exercise_attempt_id)

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
        exercise_score=canonical.score if canonical else None,
        technical_status=canonical.technical_status.value if canonical else "INVALID",
        score_eligible=canonical.score_eligible if canonical else False,
        manual_review_required=canonical.manual_review_required if canonical else True,
        quality_reasons=canonical.quality_reasons if canonical else ["MISSING_CANONICAL_SCORE"],
        scoring_components=canonical.scoring_components if canonical else {},
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
        exercise_score_repo=SQLAlchemyExerciseScoreRepository(db),
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
            _review = metrics.review_json or {}
            _reasons = list(_review.get("reasons") or [])
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
                review_required=bool(_review.get("required")),
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
        exercise_score=result.exercise_score,
        technical_status=result.technical_status,
        score_eligible=result.score_eligible,
        manual_review_required=result.manual_review_required,
        quality_reasons=result.quality_reasons or [],
        scoring_components=result.scoring_components or {},
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
    score_repo = SQLAlchemyExerciseScoreRepository(db)

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
        _review = metrics.review_json or {}
        _reasons = list(_review.get("reasons") or [])
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
            review_required=bool(_review.get("required")),
            review_reasons=_reasons,
            char_accuracy=_c_acc,
            word_accuracy=_w_acc,
        )

    canonical = score_repo.find_by_exercise_attempt_id(exercise_attempt_id)
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
        exercise_score=canonical.score if canonical else None,
        technical_status=canonical.technical_status.value if canonical else "INVALID",
        score_eligible=canonical.score_eligible if canonical else False,
        manual_review_required=canonical.manual_review_required if canonical else True,
        quality_reasons=canonical.quality_reasons if canonical else ["MISSING_CANONICAL_SCORE"],
        scoring_components=canonical.scoring_components if canonical else {},
    )


def _build_exercise_summaries(db: Session, attempt_id: UUID) -> list[ExerciseSummary]:
    ea_repo = SQLAlchemyExerciseAttemptRepository(db)
    te_repo = SQLAlchemyTemplateExerciseRepository(db)
    ex_repo = SQLAlchemyExerciseRepository(db)
    score_repo = SQLAlchemyExerciseScoreRepository(db)

    exercise_attempts = ea_repo.find_by_assessment_attempt_id(attempt_id)
    summaries = []
    for ea in exercise_attempts:
        te = te_repo.find_by_id(ea.template_exercise_id)
        if not te:
            continue
        exercise = ex_repo.find_by_id(te.exercise_id)
        if not exercise:
            continue

        canonical = score_repo.find_by_exercise_attempt_id(ea.id)

        summaries.append(
            ExerciseSummary(
                exercise_attempt_id=ea.id,
                exercise_id=exercise.id,
                order_index=te.order_index,
                type=exercise.type.value,
                title=exercise.title,
                status=ea.status.value,
                score=round(canonical.score, 2) if canonical and canonical.score is not None else None,
                review_required=canonical.manual_review_required if canonical else True,
                technical_status=canonical.technical_status.value if canonical else "INVALID",
                score_eligible=canonical.score_eligible if canonical else False,
                quality_reasons=canonical.quality_reasons if canonical else ["MISSING_CANONICAL_SCORE"],
                scoring_components=canonical.scoring_components if canonical else {},
            )
        )

    summaries.sort(key=lambda s: s.order_index)
    return summaries


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
        exercise_score_repo=SQLAlchemyExerciseScoreRepository(db),
        result_repo=SQLAlchemyAssessmentResultRepository(db),
    )
    try:
        result = uc.execute(FinishAssessmentAttemptCommand(attempt_id=attempt_id))
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()

    exercise_summaries = _build_exercise_summaries(db, attempt_id)

    scoring_snapshot = result.scoring_snapshot_json or []
    scoring_contract = _phase2_scoring_contract(
        scoring_snapshot,
        score_denominator=result.score_denominator,
        total_exercises=result.total_exercises,
        evaluated_exercises=result.evaluated_exercises,
    )

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
        score_denominator=result.score_denominator,
        scoring_snapshot=scoring_snapshot,
        exercise_summaries=exercise_summaries,
        **scoring_contract,
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

    exercise_summaries = _build_exercise_summaries(db, attempt_id)

    scoring_snapshot = result.scoring_snapshot or []
    scoring_contract = _phase2_scoring_contract(
        scoring_snapshot,
        score_denominator=result.score_denominator,
        total_exercises=result.total_exercises,
        evaluated_exercises=result.evaluated_exercises,
    )

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
        score_denominator=result.score_denominator,
        scoring_snapshot=scoring_snapshot,
        exercise_summaries=exercise_summaries,
        **scoring_contract,
    )


@router.get(
    "/attempts/{attempt_id}/review",
    response_model=ReviewResultResponse,
)
def get_attempt_review(
    attempt_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ReviewResultResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)

    attempt_repo = SQLAlchemyAssessmentAttemptRepository(db)
    attempt = attempt_repo.find_by_id(attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    student_orm = _get_student_if_owned_by_teacher(db, attempt.student_id, teacher_id)

    classroom_info = None
    cls = db.get(ClassroomModel, student_orm.classroom_id)
    if cls:
        classroom_info = {"classroom_id": str(cls.id), "name": cls.name, "grade_level": cls.grade_level, "section": cls.section}

    student_info = StudentInfo(
        student_id=student_orm.id,
        code=student_orm.code,
        age=student_orm.age,
        gender=student_orm.gender.value if hasattr(student_orm.gender, 'value') else student_orm.gender,
        classroom=classroom_info,
    )

    assessment_repo = SQLAlchemyAssessmentRepository(db)
    assessment = assessment_repo.find_by_id(attempt.assessment_id)
    assessment_dict = None
    if assessment:
        assessment_dict = {
            "assessment_id": str(assessment.id),
            "template_id": str(assessment.template_id),
            "title": assessment.title or "Untitled",
        }

    result_repo = SQLAlchemyAssessmentResultRepository(db)
    result = result_repo.find_by_attempt_id(attempt_id)
    result_response = None
    if result:
        scoring_snapshot = result.scoring_snapshot_json or []
        scoring_contract = _phase2_scoring_contract(
            scoring_snapshot,
            score_denominator=result.score_denominator,
            total_exercises=result.total_exercises if hasattr(result, 'total_exercises') else 0,
            evaluated_exercises=result.evaluated_exercises if hasattr(result, 'evaluated_exercises') else 0,
        )
        result_response = AssessmentResultResponse(
            attempt_id=attempt.id,
            final_score=result.final_score,
            max_score=result.max_score,
            mc_correct_count=result.mc_correct_count,
            os_correct_count=result.os_correct_count,
            speaking_completed_count=result.speaking_completed_count,
            writing_completed_count=result.writing_completed_count,
            intervention_level=result.intervention_level.value if result.intervention_level else None,
            generated_at=result.generated_at,
            speaking_average_score=result.speaking_average_score if hasattr(result, 'speaking_average_score') else None,
            speaking_review_required_count=result.speaking_review_required_count if hasattr(result, 'speaking_review_required_count') else 0,
            total_exercises=result.total_exercises if hasattr(result, 'total_exercises') else 0,
            evaluated_exercises=result.evaluated_exercises if hasattr(result, 'evaluated_exercises') else 0,
            pending_exercises=result.total_exercises - result.evaluated_exercises if hasattr(result, 'total_exercises') and hasattr(result, 'evaluated_exercises') else 0,
            writing_average_score=result.writing_average_score if hasattr(result, 'writing_average_score') else None,
            writing_review_required_count=result.writing_review_required_count if hasattr(result, 'writing_review_required_count') else 0,
            score_denominator=result.score_denominator,
            scoring_snapshot=scoring_snapshot,
            **scoring_contract,
        )

    ea_repo = SQLAlchemyExerciseAttemptRepository(db)
    te_repo = SQLAlchemyTemplateExerciseRepository(db)
    ex_repo = SQLAlchemyExerciseRepository(db)
    mc_opt_repo = SQLAlchemyMCAnswerOptionRepository(db)
    mc_q_repo = SQLAlchemyMCQuestionRepository(db)
    os_q_repo = SQLAlchemyOSQuestionRepository(db)
    os_a_repo = SQLAlchemyOSAnswerRepository(db)
    prompt_repo = SQLAlchemyPromptExerciseRepository(db)
    expected_repo = SQLAlchemyExpectedAnswerRepository(db)
    mc_resp_repo = SQLAlchemyMCResponseRepository(db)
    os_resp_repo = SQLAlchemyOSResponseRepository(db)
    speaking_resp_repo = SQLAlchemySpeakingResponseRepository(db)
    speaking_metrics_repo = SQLAlchemySpeakingMetricsRepository(db)
    writing_resp_repo = SQLAlchemyWritingResponseRepository(db)
    writing_metrics_repo = SQLAlchemyWritingMetricsRepository(db)
    score_repo = SQLAlchemyExerciseScoreRepository(db)
    storage = AzureAssessmentBlobStorage(get_settings())

    exercise_attempts = ea_repo.find_by_assessment_attempt_id(attempt_id)

    te_map = {}
    if assessment:
        template_exercises = te_repo.find_by_template_id(assessment.template_id)
        te_map = {te.id: te for te in template_exercises}

    exercise_reviews = []
    for ea in exercise_attempts:
        te = te_map.get(ea.template_exercise_id) or te_repo.find_by_id(ea.template_exercise_id)
        if not te:
            continue
        exercise = ex_repo.find_by_id(te.exercise_id)
        if not exercise:
            continue

        etype = exercise.type
        score = None
        response_data = None
        expected_data = None
        metrics_data = None
        review_required = False
        review_reasons = []
        question_text = None
        prompt_text = None
        reference_text = None

        if etype == ExerciseType.MULTIPLE_CHOICE:
            mc_resp = mc_resp_repo.find_by_exercise_attempt_id(ea.id)
            mc_q = mc_q_repo.find_by_exercise_id(exercise.id)
            if mc_q:
                question_text = mc_q.question_text
            if mc_resp:
                option = mc_opt_repo.find_by_id(mc_resp.selected_option_id)
                response_data = MCResponseReview(
                    selected_option_id=mc_resp.selected_option_id,
                    selected_text=option.text if option else None,
                    is_correct=mc_resp.is_correct,
                )
            if mc_q:
                correct_opts = [o for o in mc_opt_repo.find_by_question_id(mc_q.id) if o.is_correct]
                if correct_opts:
                    expected_data = MCExpectedReview(
                        correct_option_id=correct_opts[0].id,
                        correct_text=correct_opts[0].text,
                    )

        elif etype == ExerciseType.ORDER_SYLLABLES:
            os_resp = os_resp_repo.find_by_exercise_attempt_id(ea.id)
            os_q = os_q_repo.find_by_exercise_id(exercise.id)
            if os_q:
                question_text = os_q.question_text
            if os_resp:
                response_data = OSResponseReview(
                    selected_syllables=os_resp.selected_syllables_json,
                    formed_word=os_resp.formed_word,
                    is_correct=os_resp.is_correct,
                )
            if os_q:
                os_a = os_a_repo.find_by_question_id(os_q.id)
                if os_a:
                    expected_data = OSExpectedReview(
                        correct_word=os_a.correct_word,
                        syllables_json=os_a.syllables_json,
                    )

        elif etype in (ExerciseType.READING_SPEAKING, ExerciseType.LISTENING_SPEAKING):
            prompt = prompt_repo.find_by_exercise_id(exercise.id)
            if prompt:
                prompt_text = prompt.prompt_text
                expected_answer = expected_repo.find_by_prompt_exercise_id(prompt.id)
                reference_text = expected_answer.expected_text if expected_answer else prompt.text_to_show
            speaking_resp = speaking_resp_repo.find_by_exercise_attempt_id(ea.id)
            if speaking_resp:
                audio_url = None
                try:
                    audio_url = storage.download_url(blob_path=speaking_resp.audio_blob_path)
                except Exception:
                    pass
                response_data = SpeakingResponseReview(
                    audio_blob_path=speaking_resp.audio_blob_path,
                    audio_url=audio_url,
                    free_transcription_text=speaking_resp.free_transcription_text,
                    assessment_recognized_text=speaking_resp.assessment_recognized_text,
                    recognized_text=speaking_resp.recognized_text,
                )
            metrics = speaking_metrics_repo.find_by_speaking_response_id(speaking_resp.id if speaking_resp else None)
            if metrics:
                comparison = metrics.comparison_json or {}
                review = metrics.review_json or {}
                metrics_data = SpeakingMetricsReview(
                    pronunciation_score=metrics.pronunciation_score,
                    accuracy_score=metrics.accuracy_score,
                    fluency_score=metrics.fluency_score,
                    completeness_score=metrics.completeness_score,
                    prosody_score=metrics.prosody_score,
                    lexical_match=comparison.get("lexical_match_percentage"),
                    wer_percentage=comparison.get("wer_percentage"),
                )
                review_required = review.get("required", False)
                review_reasons = review.get("reasons", [])

        elif etype in (ExerciseType.READING_WRITING, ExerciseType.LISTENING_WRITING):
            prompt = prompt_repo.find_by_exercise_id(exercise.id)
            if prompt:
                prompt_text = prompt.prompt_text
                expected_answer = expected_repo.find_by_prompt_exercise_id(prompt.id)
                reference_text = expected_answer.expected_text if expected_answer else prompt.text_to_show
            writing_resp = writing_resp_repo.find_by_exercise_attempt_id(ea.id)
            if writing_resp:
                image_url = None
                try:
                    image_url = storage.download_url(blob_path=writing_resp.image_blob_path)
                except Exception:
                    pass
                response_data = WritingResponseReview(
                    image_blob_path=writing_resp.image_blob_path,
                    image_url=image_url,
                    recognized_text=writing_resp.recognized_text,
                    original_filename=writing_resp.original_filename,
                    content_type=writing_resp.content_type,
                )
            metrics = writing_metrics_repo.find_by_writing_response_id(writing_resp.id if writing_resp else None)
            if metrics:
                writing_review = metrics.review_json or {}
                reasons_list = list(writing_review.get("reasons") or [])
                review_required = bool(writing_review.get("required"))
                review_reasons = reasons_list
                metrics_data = WritingMetricsReview(
                    confidence_avg=metrics.confidence_avg,
                    cer=metrics.cer,
                    wer=metrics.wer,
                    similarity_score=metrics.similarity_score,
                    char_accuracy=round(max(0.0, 100.0 * (1.0 - (metrics.cer or 0))), 2) if metrics.cer is not None else None,
                    word_accuracy=round(max(0.0, 100.0 * (1.0 - (metrics.wer or 0))), 2) if metrics.wer is not None else None,
                    duration_ms=metrics.duration_ms,
                    stroke_count=metrics.stroke_count,
                    point_count=metrics.point_count,
                    pause_count=metrics.pause_count,
                    longest_pause_ms=metrics.longest_pause_ms,
                    total_pause_time_ms=metrics.total_pause_time_ms,
                    average_speed=metrics.average_speed,
                    speed_variability=metrics.speed_variability,
                    writing_area_usage=metrics.writing_area_usage,
                )

        canonical = score_repo.find_by_exercise_attempt_id(ea.id)
        score = canonical.score if canonical else None
        review_required = canonical.manual_review_required if canonical else True
        review_reasons = canonical.quality_reasons if canonical else ["MISSING_CANONICAL_SCORE"]
        exercise_reviews.append(
            ExerciseReview(
                exercise_attempt_id=ea.id,
                exercise_id=exercise.id,
                order_index=te.order_index,
                type=exercise.type.value,
                title=exercise.title,
                instructions=exercise.instructions,
                status=ea.status.value,
                score=round(score, 2) if score is not None else None,
                question_text=question_text,
                prompt_text=prompt_text,
                reference_text=reference_text,
                response=response_data,
                expected=expected_data,
                metrics=metrics_data,
                review_required=review_required,
                review_reasons=review_reasons,
                technical_status=canonical.technical_status.value if canonical else "INVALID",
                score_eligible=canonical.score_eligible if canonical else False,
                quality_reasons=canonical.quality_reasons if canonical else ["MISSING_CANONICAL_SCORE"],
                scoring_components=canonical.scoring_components if canonical else {},
            )
        )

    exercise_reviews.sort(key=lambda r: r.order_index)

    return ReviewResultResponse(
        attempt_id=attempt.id,
        status=attempt.status.value,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        student=student_info,
        assessment=assessment_dict,
        result=result_response,
        exercise_reviews=exercise_reviews,
    )


@router.get(
    "/students/{student_id}/history",
    response_model=StudentAssessmentHistoryResponse,
)
def get_student_assessment_history(
    student_id: UUID,
    limit: int = 20,
    offset: int = 0,
    status: str | None = "COMPLETED",
    assessment_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentAssessmentHistoryResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)

    student = _get_student_if_owned_by_teacher(db, student_id, teacher_id)

    uc = GetStudentAssessmentHistoryUseCase(
        attempt_repo=SQLAlchemyAssessmentAttemptRepository(db),
        result_repo=SQLAlchemyAssessmentResultRepository(db),
        assessment_repo=SQLAlchemyAssessmentRepository(db),
    )
    try:
        result = uc.execute(
            GetStudentAssessmentHistoryQuery(
                student_id=student_id,
                limit=limit,
                offset=offset,
                status=status,
                assessment_id=assessment_id,
                date_from=date_from,
                date_to=date_to,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    classroom_info = None
    if student and student.classroom_id:
        cls = db.get(ClassroomModel, student.classroom_id)
        if cls:
            classroom_info = StudentClassroomInfo(
                classroom_id=cls.id,
                name=cls.name,
                grade_level=cls.grade_level,
                section=cls.section,
            ).model_dump()

    student_info = None
    if student:
        from app.school.domain.enums import Gender
        student_info = StudentInfo(
            student_id=student.id,
            code=student.code,
            age=student.age,
            gender=student.gender.value if hasattr(student.gender, 'value') else student.gender,
            classroom=classroom_info,
        )

    chart_points = []
    for item in result.items:
        if item.status == "COMPLETED" and item.completed_at is not None:
            chart_points.append(
                ChartPoint(
                    attempt_id=item.attempt_id,
                    assessment_id=item.assessment_id,
                    assessment_name=item.assessment_name,
                    completed_at=item.completed_at,
                    final_score=item.final_score,
                    intervention_level=item.intervention_level,
                )
            )
    chart_points.sort(key=lambda cp: cp.completed_at or datetime.min)

    from dataclasses import asdict
    from app.assessment.presentation.schemas import (
        StudentAssessmentHistoryItem as HistoryItemSchema,
        StudentAssessmentHistorySummary as SummarySchema,
    )

    return StudentAssessmentHistoryResponse(
        student_id=result.student_id,
        student=student_info,
        summary=SummarySchema(**asdict(result.summary)),
        chart_points=chart_points,
        items=[HistoryItemSchema(**asdict(item)) for item in result.items],
        total=result.summary.attempts_count,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/students/{student_id}/attempts",
    response_model=StudentAttemptListResponse,
)
def list_student_attempts(
    student_id: UUID,
    status: str | None = None,
    assessment_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentAttemptListResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)
    _get_student_if_owned_by_teacher(db, student_id, teacher_id)

    attempt_repo = SQLAlchemyAssessmentAttemptRepository(db)
    result_repo = SQLAlchemyAssessmentResultRepository(db)
    assessment_repo = SQLAlchemyAssessmentRepository(db)

    attempts = attempt_repo.find_by_student_id(
        student_id,
        status=status,
        assessment_id=assessment_id,
        limit=limit,
        offset=offset,
    )

    items = []
    for a in attempts:
        result = result_repo.find_by_attempt_id(a.id)
        assessment = assessment_repo.find_by_id(a.assessment_id)
        assessment_name = assessment.title or "Untitled" if assessment else None

        items.append(
            StudentAttemptItem(
                attempt_id=a.id,
                assessment_id=a.assessment_id,
                assessment_name=assessment_name,
                status=a.status.value,
                started_at=a.started_at,
                completed_at=a.completed_at,
                final_score=result.final_score if result else None,
                max_score=result.max_score if result else None,
                intervention_level=result.intervention_level.value if result and result.intervention_level else None,
                total_exercises=result.total_exercises if result else 0,
                evaluated_exercises=result.evaluated_exercises if result else 0,
                pending_exercises=result.total_exercises - result.evaluated_exercises if result else 0,
            )
        )

    total_attempts = attempt_repo.find_by_student_id(
        student_id,
        status=status,
        assessment_id=assessment_id,
    )

    return StudentAttemptListResponse(
        student_id=student_id,
        items=items,
        total=len(total_attempts),
        limit=limit,
        offset=offset,
    )


@router.post(
    "/attempts/{attempt_id}/repeat",
    response_model=RepeatAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def repeat_attempt(
    attempt_id: UUID,
    request: RepeatAttemptRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> RepeatAttemptResponse:
    _resolve_teacher_id(db, current_user.id)
    uc = RepeatAssessmentAttemptUseCase(
        attempt_repo=SQLAlchemyAssessmentAttemptRepository(db),
        exercise_attempt_repo=SQLAlchemyExerciseAttemptRepository(db),
        template_exercise_repo=SQLAlchemyTemplateExerciseRepository(db),
        exercise_repo=SQLAlchemyExerciseRepository(db),
        assessment_repo=SQLAlchemyAssessmentRepository(db),
    )
    try:
        result = uc.execute(
            RepeatAssessmentAttemptCommand(
                attempt_id=attempt_id,
                reason=request.reason,
            )
        )
    except AssessmentException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    db.commit()
    return RepeatAttemptResponse(
        original_attempt_id=attempt_id,
        new_attempt_id=result.attempt_id,
        assessment_id=result.assessment_id,
        student_id=result.student_id,
        status=result.status.value,
        reason=request.reason,
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
