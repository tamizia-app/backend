from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.assessment.application.ports.repositories import (
    AssessmentAttemptRepository,
    AssessmentRepository,
    AssessmentResultRepository,
    ExerciseAttemptRepository,
    ExerciseScoreRepository,
    ExerciseRepository,
    ExpectedAnswerRepository,
    MCAnswerOptionRepository,
    MCQuestionRepository,
    MCResponseRepository,
    OSAnswerRepository,
    OSQuestionRepository,
    OSResponseRepository,
    PromptExerciseRepository,
    SpeakingMetricsRepository,
    SpeakingResponseRepository,
    TemplateExerciseRepository,
    TemplateRepository,
    WritingMetricsRepository,
    WritingResponseRepository,
    ManualReviewEventRepository,
)
from app.assessment.domain.assessment import Assessment
from app.assessment.domain.attempt import AssessmentAttempt, ExerciseAttempt
from app.assessment.domain.enums import (
    AssessmentStatus,
    AttemptStatus,
    ExerciseAttemptStatus,
    ExerciseType,
    InterventionLevel,
    TechnicalStatus,
)
from app.assessment.domain.exercise import AssessmentExercise
from app.assessment.domain.metrics import AssessmentResult as AssessmentResultDomain
from app.assessment.domain.metrics import ExerciseScore, ManualReviewEvent, SpeakingMetrics, WritingMetrics
from app.assessment.domain.prompt import ExpectedAnswer, PromptExercise
from app.assessment.domain.question import MCAnswerOption, MCQuestion, OSAnswer, OSQuestion
from app.assessment.domain.response import MCResponse, OSResponse, SpeakingResponse, WritingResponse
from app.assessment.domain.template import AssessmentTemplate, AssessmentTemplateExercise
from app.assessment.infrastructure.models.assessment_model import AssessmentModel
from app.assessment.infrastructure.models.attempt_model import (
    AssessmentAttemptModel,
    ExerciseAttemptModel,
)
from app.assessment.infrastructure.models.exercise_model import AssessmentExerciseModel
from app.assessment.infrastructure.models.metrics_model import (
    AssessmentResultModel,
    ExerciseScoreModel,
    ManualReviewEventModel,
    SpeakingMetricsModel,
    WritingMetricsModel,
)
from app.assessment.infrastructure.models.prompt_model import (
    ExpectedAnswerModel,
    PromptExerciseModel,
)
from app.assessment.infrastructure.models.question_model import (
    MCAnswerOptionModel,
    MCQuestionModel,
    OSAnswerModel,
    OSQuestionModel,
)
from app.assessment.infrastructure.models.response_model import (
    MCResponseModel,
    OSResponseModel,
    SpeakingResponseModel,
    WritingResponseModel,
)
from app.assessment.infrastructure.models.template_model import (
    AssessmentTemplateExerciseModel,
    AssessmentTemplateModel,
)


class SQLAlchemyTemplateRepository(TemplateRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, template_id: UUID) -> AssessmentTemplate | None:
        model = self._db.get(AssessmentTemplateModel, template_id)
        return self._to_domain(model) if model else None

    def find_by_teacher_id(self, teacher_id: UUID) -> list[AssessmentTemplate]:
        models = self._db.scalars(
            select(AssessmentTemplateModel)
            .where(AssessmentTemplateModel.created_by_teacher_id == teacher_id)
            .order_by(AssessmentTemplateModel.created_at.desc())
        )
        return [self._to_domain(m) for m in models]

    def find_visible_by_teacher_id(self, teacher_id: UUID) -> list[AssessmentTemplate]:
        models = self._db.scalars(
            select(AssessmentTemplateModel)
            .where(AssessmentTemplateModel.is_active.is_(True))
            .where(
                or_(
                    AssessmentTemplateModel.created_by_teacher_id == teacher_id,
                    AssessmentTemplateModel.created_by_teacher_id.is_(None),
                )
            )
            .order_by(AssessmentTemplateModel.created_at.desc())
        )
        return [self._to_domain(m) for m in models]

    def find_accessible_by_id(self, template_id: UUID, teacher_id: UUID) -> AssessmentTemplate | None:
        model = self._db.scalar(
            select(AssessmentTemplateModel)
            .where(AssessmentTemplateModel.id == template_id)
            .where(AssessmentTemplateModel.is_active.is_(True))
            .where(
                or_(
                    AssessmentTemplateModel.created_by_teacher_id == teacher_id,
                    AssessmentTemplateModel.created_by_teacher_id.is_(None),
                )
            )
        )
        return self._to_domain(model) if model else None

    def find_owned_by_id(self, template_id: UUID, teacher_id: UUID) -> AssessmentTemplate | None:
        model = self._db.scalar(
            select(AssessmentTemplateModel)
            .where(AssessmentTemplateModel.id == template_id)
            .where(AssessmentTemplateModel.created_by_teacher_id == teacher_id)
        )
        return self._to_domain(model) if model else None

    def create(self, template: AssessmentTemplate) -> AssessmentTemplate:
        model = AssessmentTemplateModel(
            name=template.name,
            description=template.description,
            version=template.version,
            is_active=template.is_active,
            created_by_teacher_id=template.created_by_teacher_id if template.created_by_teacher_id else None,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, template: AssessmentTemplate) -> AssessmentTemplate:
        model = self._db.get(AssessmentTemplateModel, template.id)
        if model:
            model.name = template.name
            model.description = template.description
            model.version = template.version
            model.is_active = template.is_active
            self._db.flush()
        return template

    def delete(self, template_id: UUID) -> None:
        model = self._db.get(AssessmentTemplateModel, template_id)
        if model:
            self._db.delete(model)
            self._db.flush()

    def has_history(self, template_id: UUID) -> bool:
        assessment_id = self._db.scalar(
            select(AssessmentModel.id)
            .where(AssessmentModel.template_id == template_id)
            .limit(1)
        )
        if assessment_id:
            return True

        exercise_attempt_id = self._db.scalar(
            select(ExerciseAttemptModel.id)
            .join(
                AssessmentTemplateExerciseModel,
                ExerciseAttemptModel.template_exercise_id == AssessmentTemplateExerciseModel.id,
            )
            .where(AssessmentTemplateExerciseModel.template_id == template_id)
            .limit(1)
        )
        return bool(exercise_attempt_id)

    @staticmethod
    def _to_domain(model: AssessmentTemplateModel) -> AssessmentTemplate:
        return AssessmentTemplate(
            id=model.id,
            name=model.name,
            description=model.description,
            version=model.version,
            is_active=model.is_active,
            created_by_teacher_id=model.created_by_teacher_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyTemplateExerciseRepository(TemplateExerciseRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, te_id: UUID) -> AssessmentTemplateExercise | None:
        model = self._db.get(AssessmentTemplateExerciseModel, te_id)
        return self._to_domain(model) if model else None

    def find_by_template_id(self, template_id: UUID) -> list[AssessmentTemplateExercise]:
        models = self._db.scalars(
            select(AssessmentTemplateExerciseModel)
            .where(AssessmentTemplateExerciseModel.template_id == template_id)
            .order_by(AssessmentTemplateExerciseModel.order_index)
        )
        return [self._to_domain(m) for m in models]

    def create(self, te: AssessmentTemplateExercise) -> AssessmentTemplateExercise:
        model = AssessmentTemplateExerciseModel(
            template_id=te.template_id,
            exercise_id=te.exercise_id,
            order_index=te.order_index,
            points=te.points,
            is_required=te.is_required,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update_points(self, template_exercise_id: UUID, points: int) -> AssessmentTemplateExercise:
        model = self._db.get(AssessmentTemplateExerciseModel, template_exercise_id)
        if not model:
            raise ValueError("Template exercise not found.")
        model.points = points
        self._db.flush()
        return self._to_domain(model)

    def delete_by_template_id(self, template_id: UUID) -> None:
        self._db.query(AssessmentTemplateExerciseModel).filter(
            AssessmentTemplateExerciseModel.template_id == template_id
        ).delete()
        self._db.flush()

    def find_invalid_points_by_teacher_id(self, teacher_id: UUID) -> list[dict]:
        rows = self._db.execute(
            select(
                AssessmentTemplateModel.id.label("template_id"),
                AssessmentTemplateModel.name.label("template_name"),
                AssessmentTemplateModel.version.label("template_version"),
                AssessmentTemplateModel.is_active.label("is_active"),
                AssessmentTemplateExerciseModel.id.label("template_exercise_id"),
                AssessmentTemplateExerciseModel.exercise_id.label("exercise_id"),
                AssessmentExerciseModel.type.label("exercise_type"),
                AssessmentTemplateExerciseModel.order_index.label("order_index"),
                AssessmentTemplateExerciseModel.points.label("current_points"),
            )
            .join(
                AssessmentTemplateExerciseModel,
                AssessmentTemplateExerciseModel.template_id == AssessmentTemplateModel.id,
            )
            .join(
                AssessmentExerciseModel,
                AssessmentExerciseModel.id == AssessmentTemplateExerciseModel.exercise_id,
            )
            .where(AssessmentTemplateModel.created_by_teacher_id == teacher_id)
            .where(~AssessmentTemplateExerciseModel.points.in_([1, 2, 3]))
            .order_by(
                AssessmentTemplateModel.name,
                AssessmentTemplateModel.version,
                AssessmentTemplateExerciseModel.order_index,
            )
        )
        return [dict(row._mapping) for row in rows]

    @staticmethod
    def _to_domain(model: AssessmentTemplateExerciseModel) -> AssessmentTemplateExercise:
        return AssessmentTemplateExercise(
            id=model.id,
            template_id=model.template_id,
            exercise_id=model.exercise_id,
            order_index=model.order_index,
            points=model.points,
            is_required=model.is_required,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyExerciseRepository(ExerciseRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, exercise_id: UUID) -> AssessmentExercise | None:
        model = self._db.get(AssessmentExerciseModel, exercise_id)
        return self._to_domain(model) if model else None

    def find_by_ids(self, ids: list[UUID]) -> list[AssessmentExercise]:
        models = self._db.scalars(
            select(AssessmentExerciseModel).where(AssessmentExerciseModel.id.in_(ids))
        )
        return [self._to_domain(m) for m in models]

    def find_all(
        self,
        *,
        type_filter: str | None = None,
        difficulty_level: int | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AssessmentExercise]:
        stmt = select(AssessmentExerciseModel).order_by(AssessmentExerciseModel.created_at.desc())
        if type_filter:
            stmt = stmt.where(AssessmentExerciseModel.type == type_filter)
        if difficulty_level is not None:
            stmt = stmt.where(AssessmentExerciseModel.difficulty_level == difficulty_level)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                (AssessmentExerciseModel.title.ilike(pattern))
                | (AssessmentExerciseModel.instructions.ilike(pattern))
            )
        models = self._db.scalars(stmt.offset(offset).limit(limit))
        return [self._to_domain(m) for m in models]

    def create(self, exercise: AssessmentExercise) -> AssessmentExercise:
        model = AssessmentExerciseModel(
            type=exercise.type.value,
            title=exercise.title,
            instructions=exercise.instructions,
            stimulus_type=exercise.stimulus_type,
            response_type=exercise.response_type,
            difficulty_level=exercise.difficulty_level,
            is_active=exercise.is_active,
            created_by_teacher_id=exercise.created_by_teacher_id if exercise.created_by_teacher_id else None,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: AssessmentExerciseModel) -> AssessmentExercise:
        return AssessmentExercise(
            id=model.id,
            type=ExerciseType(model.type),
            title=model.title,
            instructions=model.instructions,
            stimulus_type=model.stimulus_type,
            response_type=model.response_type,
            difficulty_level=model.difficulty_level,
            is_active=model.is_active,
            created_by_teacher_id=model.created_by_teacher_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyOSQuestionRepository(OSQuestionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_exercise_id(self, exercise_id: UUID) -> OSQuestion | None:
        model = self._db.scalar(
            select(OSQuestionModel).where(OSQuestionModel.exercise_id == exercise_id)
        )
        return self._to_domain(model) if model else None

    def create(self, q: OSQuestion) -> OSQuestion:
        model = OSQuestionModel(
            exercise_id=q.exercise_id,
            question_text=q.question_text,
            image_blob_path=q.image_blob_path,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: OSQuestionModel) -> OSQuestion:
        return OSQuestion(
            id=model.id,
            exercise_id=model.exercise_id,
            question_text=model.question_text,
            image_blob_path=model.image_blob_path,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyOSAnswerRepository(OSAnswerRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_question_id(self, question_id: UUID) -> OSAnswer | None:
        model = self._db.scalar(
            select(OSAnswerModel).where(OSAnswerModel.os_question_id == question_id)
        )
        return self._to_domain(model) if model else None

    def create(self, a: OSAnswer) -> OSAnswer:
        model = OSAnswerModel(
            os_question_id=a.os_question_id,
            correct_word=a.correct_word,
            syllables_json=a.syllables_json,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: OSAnswerModel) -> OSAnswer:
        return OSAnswer(
            id=model.id,
            os_question_id=model.os_question_id,
            correct_word=model.correct_word,
            syllables_json=model.syllables_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyMCQuestionRepository(MCQuestionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_exercise_id(self, exercise_id: UUID) -> MCQuestion | None:
        model = self._db.scalar(
            select(MCQuestionModel).where(MCQuestionModel.exercise_id == exercise_id)
        )
        return self._to_domain(model) if model else None

    def create(self, q: MCQuestion) -> MCQuestion:
        model = MCQuestionModel(
            exercise_id=q.exercise_id,
            question_text=q.question_text,
            image_blob_path=q.image_blob_path,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, q: MCQuestion) -> MCQuestion:
        model = self._db.get(MCQuestionModel, q.id)
        if model:
            model.question_text = q.question_text
            model.image_blob_path = q.image_blob_path
            self._db.flush()
        return q

    @staticmethod
    def _to_domain(model: MCQuestionModel) -> MCQuestion:
        return MCQuestion(
            id=model.id,
            exercise_id=model.exercise_id,
            question_text=model.question_text,
            image_blob_path=model.image_blob_path,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyMCAnswerOptionRepository(MCAnswerOptionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_question_id(self, question_id: UUID) -> list[MCAnswerOption]:
        models = self._db.scalars(
            select(MCAnswerOptionModel)
            .where(MCAnswerOptionModel.mc_question_id == question_id)
            .order_by(MCAnswerOptionModel.order_index)
        )
        return [self._to_domain(m) for m in models]

    def find_by_id(self, option_id: UUID) -> MCAnswerOption | None:
        model = self._db.get(MCAnswerOptionModel, option_id)
        return self._to_domain(model) if model else None

    def create(self, opt: MCAnswerOption) -> MCAnswerOption:
        model = MCAnswerOptionModel(
            mc_question_id=opt.mc_question_id,
            text=opt.text,
            is_correct=opt.is_correct,
            order_index=opt.order_index,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def create_many(self, opts: list[MCAnswerOption]) -> list[MCAnswerOption]:
        results = []
        for opt in opts:
            results.append(self.create(opt))
        return results

    @staticmethod
    def _to_domain(model: MCAnswerOptionModel) -> MCAnswerOption:
        return MCAnswerOption(
            id=model.id,
            mc_question_id=model.mc_question_id,
            text=model.text,
            is_correct=model.is_correct,
            order_index=model.order_index,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyPromptExerciseRepository(PromptExerciseRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_exercise_id(self, exercise_id: UUID) -> PromptExercise | None:
        model = self._db.scalar(
            select(PromptExerciseModel).where(PromptExerciseModel.exercise_id == exercise_id)
        )
        return self._to_domain(model) if model else None

    def create(self, p: PromptExercise) -> PromptExercise:
        model = PromptExerciseModel(
            exercise_id=p.exercise_id,
            prompt_text=p.prompt_text,
            text_to_show=p.text_to_show,
            audio_blob_path=p.audio_blob_path,
            image_blob_path=p.image_blob_path,
            language_code=p.language_code,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: PromptExerciseModel) -> PromptExercise:
        return PromptExercise(
            id=model.id,
            exercise_id=model.exercise_id,
            prompt_text=model.prompt_text,
            text_to_show=model.text_to_show,
            audio_blob_path=model.audio_blob_path,
            image_blob_path=model.image_blob_path,
            language_code=model.language_code,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyExpectedAnswerRepository(ExpectedAnswerRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_prompt_exercise_id(self, prompt_exercise_id: UUID) -> ExpectedAnswer | None:
        model = self._db.scalar(
            select(ExpectedAnswerModel).where(
                ExpectedAnswerModel.prompt_exercise_id == prompt_exercise_id
            )
        )
        return self._to_domain(model) if model else None

    def create(self, a: ExpectedAnswer) -> ExpectedAnswer:
        model = ExpectedAnswerModel(
            prompt_exercise_id=a.prompt_exercise_id,
            expected_text=a.expected_text,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: ExpectedAnswerModel) -> ExpectedAnswer:
        return ExpectedAnswer(
            id=model.id,
            prompt_exercise_id=model.prompt_exercise_id,
            expected_text=model.expected_text,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyAssessmentRepository(AssessmentRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, assessment_id: UUID) -> Assessment | None:
        model = self._db.get(AssessmentModel, assessment_id)
        return self._to_domain(model) if model else None

    def find_by_teacher_id(self, teacher_id: UUID) -> list[Assessment]:
        models = self._db.scalars(
            select(AssessmentModel)
            .where(AssessmentModel.homeroom_teacher_id == teacher_id)
            .order_by(AssessmentModel.created_at.desc())
        )
        return [self._to_domain(m) for m in models]

    def create(self, assessment: Assessment) -> Assessment:
        model = AssessmentModel(
            template_id=assessment.template_id,
            classroom_id=assessment.classroom_id,
            homeroom_teacher_id=assessment.homeroom_teacher_id,
            title=assessment.title,
            status=assessment.status.value,
            scheduled_at=assessment.scheduled_at,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, assessment: Assessment) -> Assessment:
        model = self._db.get(AssessmentModel, assessment.id)
        if model:
            model.status = assessment.status.value
            model.title = assessment.title
            model.scheduled_at = assessment.scheduled_at
            self._db.flush()
        return assessment

    @staticmethod
    def _to_domain(model: AssessmentModel) -> Assessment:
        return Assessment(
            id=model.id,
            template_id=model.template_id,
            classroom_id=model.classroom_id,
            homeroom_teacher_id=model.homeroom_teacher_id,
            title=model.title,
            status=AssessmentStatus(model.status),
            scheduled_at=model.scheduled_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyAssessmentAttemptRepository(AssessmentAttemptRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, attempt_id: UUID) -> AssessmentAttempt | None:
        model = self._db.get(AssessmentAttemptModel, attempt_id)
        return self._to_domain(model) if model else None

    def find_by_assessment_id(self, assessment_id: UUID) -> list[AssessmentAttempt]:
        models = self._db.scalars(
            select(AssessmentAttemptModel).where(
                AssessmentAttemptModel.assessment_id == assessment_id
            )
        )
        return [self._to_domain(m) for m in models]

    def find_by_student_id(
        self,
        student_id: UUID,
        *,
        status: str | None = None,
        assessment_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[AssessmentAttempt]:
        conditions = [AssessmentAttemptModel.student_id == student_id]
        if status:
            conditions.append(AssessmentAttemptModel.status == status)
        if assessment_id:
            conditions.append(AssessmentAttemptModel.assessment_id == assessment_id)
        if date_from:
            conditions.append(AssessmentAttemptModel.started_at >= date_from)
        if date_to:
            conditions.append(AssessmentAttemptModel.started_at <= date_to)
        models = self._db.scalars(
            select(AssessmentAttemptModel)
            .where(and_(*conditions))
            .order_by(AssessmentAttemptModel.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [self._to_domain(m) for m in models]

    def create(self, attempt: AssessmentAttempt) -> AssessmentAttempt:
        model = AssessmentAttemptModel(
            assessment_id=attempt.assessment_id,
            student_id=attempt.student_id,
            status=attempt.status.value,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            repeated_from_attempt_id=attempt.repeated_from_attempt_id,
            repeat_reason=attempt.repeat_reason,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, attempt: AssessmentAttempt) -> AssessmentAttempt:
        model = self._db.get(AssessmentAttemptModel, attempt.id)
        if model:
            model.status = attempt.status.value
            model.completed_at = attempt.completed_at
            self._db.flush()
        return attempt

    @staticmethod
    def _to_domain(model: AssessmentAttemptModel) -> AssessmentAttempt:
        return AssessmentAttempt(
            id=model.id,
            assessment_id=model.assessment_id,
            student_id=model.student_id,
            status=AttemptStatus(model.status),
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            repeated_from_attempt_id=model.repeated_from_attempt_id,
            repeat_reason=model.repeat_reason,
        )


class SQLAlchemyExerciseAttemptRepository(ExerciseAttemptRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, ea_id: UUID) -> ExerciseAttempt | None:
        model = self._db.get(ExerciseAttemptModel, ea_id)
        return self._to_domain(model) if model else None

    def find_by_assessment_attempt_id(self, attempt_id: UUID) -> list[ExerciseAttempt]:
        models = self._db.scalars(
            select(ExerciseAttemptModel).where(
                ExerciseAttemptModel.assessment_attempt_id == attempt_id
            )
        )
        return [self._to_domain(m) for m in models]

    def create(self, ea: ExerciseAttempt) -> ExerciseAttempt:
        model = ExerciseAttemptModel(
            assessment_attempt_id=ea.assessment_attempt_id,
            template_exercise_id=ea.template_exercise_id,
            status=ea.status.value,
            started_at=ea.started_at,
            submitted_at=ea.submitted_at,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def create_many(self, eas: list[ExerciseAttempt]) -> list[ExerciseAttempt]:
        results = []
        for ea in eas:
            results.append(self.create(ea))
        return results

    def update(self, ea: ExerciseAttempt) -> ExerciseAttempt:
        model = self._db.get(ExerciseAttemptModel, ea.id)
        if model:
            model.status = ea.status.value
            model.started_at = ea.started_at
            model.submitted_at = ea.submitted_at
            self._db.flush()
        return ea

    @staticmethod
    def _to_domain(model: ExerciseAttemptModel) -> ExerciseAttempt:
        return ExerciseAttempt(
            id=model.id,
            assessment_attempt_id=model.assessment_attempt_id,
            template_exercise_id=model.template_exercise_id,
            status=ExerciseAttemptStatus(model.status),
            started_at=model.started_at,
            submitted_at=model.submitted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyMCResponseRepository(MCResponseRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_exercise_attempt_id(self, ea_id: UUID) -> MCResponse | None:
        model = self._db.scalar(
            select(MCResponseModel).where(MCResponseModel.exercise_attempt_id == ea_id)
        )
        return self._to_domain(model) if model else None

    def create(self, r: MCResponse) -> MCResponse:
        model = MCResponseModel(
            exercise_attempt_id=r.exercise_attempt_id,
            selected_option_id=r.selected_option_id,
            is_correct=r.is_correct,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, r: MCResponse) -> MCResponse:
        model = self._db.get(MCResponseModel, r.id)
        if model:
            model.selected_option_id = r.selected_option_id
            model.is_correct = r.is_correct
            self._db.flush()
        return r

    @staticmethod
    def _to_domain(model: MCResponseModel) -> MCResponse:
        return MCResponse(
            id=model.id,
            exercise_attempt_id=model.exercise_attempt_id,
            selected_option_id=model.selected_option_id,
            is_correct=model.is_correct,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyOSResponseRepository(OSResponseRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_exercise_attempt_id(self, ea_id: UUID) -> OSResponse | None:
        model = self._db.scalar(
            select(OSResponseModel).where(OSResponseModel.exercise_attempt_id == ea_id)
        )
        return self._to_domain(model) if model else None

    def create(self, r: OSResponse) -> OSResponse:
        model = OSResponseModel(
            exercise_attempt_id=r.exercise_attempt_id,
            selected_syllables_json=r.selected_syllables_json,
            formed_word=r.formed_word,
            is_correct=r.is_correct,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, r: OSResponse) -> OSResponse:
        model = self._db.get(OSResponseModel, r.id)
        if model:
            model.selected_syllables_json = r.selected_syllables_json
            model.formed_word = r.formed_word
            model.is_correct = r.is_correct
            self._db.flush()
        return r

    @staticmethod
    def _to_domain(model: OSResponseModel) -> OSResponse:
        return OSResponse(
            id=model.id,
            exercise_attempt_id=model.exercise_attempt_id,
            selected_syllables_json=model.selected_syllables_json,
            formed_word=model.formed_word,
            is_correct=model.is_correct,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemySpeakingResponseRepository(SpeakingResponseRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_exercise_attempt_id(self, ea_id: UUID) -> SpeakingResponse | None:
        model = self._db.scalar(
            select(SpeakingResponseModel).where(
                SpeakingResponseModel.exercise_attempt_id == ea_id
            )
        )
        return self._to_domain(model) if model else None

    def create(self, r: SpeakingResponse) -> SpeakingResponse:
        model = SpeakingResponseModel(
            exercise_attempt_id=r.exercise_attempt_id,
            audio_blob_path=r.audio_blob_path,
            original_filename=r.original_filename,
            content_type=r.content_type,
            duration_ms=r.duration_ms,
            recognized_text=r.recognized_text,
            free_transcription_text=r.free_transcription_text,
            assessment_recognized_text=r.assessment_recognized_text,
            reviewed_free_transcription_text=r.reviewed_free_transcription_text,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, r: SpeakingResponse) -> SpeakingResponse:
        model = self._db.get(SpeakingResponseModel, r.id)
        if model:
            model.audio_blob_path = r.audio_blob_path
            model.original_filename = r.original_filename
            model.content_type = r.content_type
            model.duration_ms = r.duration_ms
            model.recognized_text = r.recognized_text
            model.free_transcription_text = r.free_transcription_text
            model.assessment_recognized_text = r.assessment_recognized_text
            model.reviewed_free_transcription_text = r.reviewed_free_transcription_text
            self._db.flush()
        return r

    @staticmethod
    def _to_domain(model: SpeakingResponseModel) -> SpeakingResponse:
        return SpeakingResponse(
            id=model.id,
            exercise_attempt_id=model.exercise_attempt_id,
            audio_blob_path=model.audio_blob_path,
            original_filename=model.original_filename,
            content_type=model.content_type,
            duration_ms=model.duration_ms,
            recognized_text=model.recognized_text,
            free_transcription_text=model.free_transcription_text,
            assessment_recognized_text=model.assessment_recognized_text,
            reviewed_free_transcription_text=model.reviewed_free_transcription_text,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemyWritingResponseRepository(WritingResponseRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_exercise_attempt_id(self, ea_id: UUID) -> WritingResponse | None:
        model = self._db.scalar(
            select(WritingResponseModel).where(
                WritingResponseModel.exercise_attempt_id == ea_id
            )
        )
        return self._to_domain(model) if model else None

    def create(self, r: WritingResponse) -> WritingResponse:
        model = WritingResponseModel(
            exercise_attempt_id=r.exercise_attempt_id,
            image_blob_path=r.image_blob_path,
            original_filename=r.original_filename,
            content_type=r.content_type,
            recognized_text=r.recognized_text,
            reviewed_recognized_text=r.reviewed_recognized_text,
            strokes_json=r.strokes_json,
            canvas_metadata_json=r.canvas_metadata_json,
            input_metadata_json=r.input_metadata_json,
            frontend_metrics_json=r.frontend_metrics_json,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, r: WritingResponse) -> WritingResponse:
        model = self._db.get(WritingResponseModel, r.id)
        if model:
            model.image_blob_path = r.image_blob_path
            model.original_filename = r.original_filename
            model.content_type = r.content_type
            model.recognized_text = r.recognized_text
            model.reviewed_recognized_text = r.reviewed_recognized_text
            model.strokes_json = r.strokes_json
            model.canvas_metadata_json = r.canvas_metadata_json
            model.input_metadata_json = r.input_metadata_json
            model.frontend_metrics_json = r.frontend_metrics_json
            self._db.flush()
        return r

    @staticmethod
    def _to_domain(model: WritingResponseModel) -> WritingResponse:
        return WritingResponse(
            id=model.id,
            exercise_attempt_id=model.exercise_attempt_id,
            image_blob_path=model.image_blob_path,
            original_filename=model.original_filename,
            content_type=model.content_type,
            recognized_text=model.recognized_text,
            reviewed_recognized_text=model.reviewed_recognized_text,
            strokes_json=model.strokes_json,
            canvas_metadata_json=model.canvas_metadata_json,
            input_metadata_json=model.input_metadata_json,
            frontend_metrics_json=model.frontend_metrics_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemySpeakingMetricsRepository(SpeakingMetricsRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, m: SpeakingMetrics) -> SpeakingMetrics:
        model = SpeakingMetricsModel(
            speaking_response_id=m.speaking_response_id,
            pronunciation_score=m.pronunciation_score,
            accuracy_score=m.accuracy_score,
            fluency_score=m.fluency_score,
            completeness_score=m.completeness_score,
            prosody_score=m.prosody_score,
            raw_speech_result_json=m.raw_speech_result_json,
            raw_transcription_result_json=m.raw_transcription_result_json,
            comparison_json=m.comparison_json,
            review_json=m.review_json,
            quality_json=m.quality_json,
            original_pronunciation_score=m.original_pronunciation_score,
            current_pronunciation_score=m.current_pronunciation_score,
            original_accuracy_score=m.original_accuracy_score,
            current_accuracy_score=m.current_accuracy_score,
            original_fluency_score=m.original_fluency_score,
            current_fluency_score=m.current_fluency_score,
            original_completeness_score=m.original_completeness_score,
            current_completeness_score=m.current_completeness_score,
            original_lexical_match=m.original_lexical_match,
            current_lexical_match=m.current_lexical_match,
            original_prosody_score=m.original_prosody_score,
            current_prosody_score=m.current_prosody_score,
        )
        self._db.add(model)
        self._db.flush()
        return m

    def find_by_speaking_response_id(self, response_id: UUID) -> SpeakingMetrics | None:
        model = self._db.scalar(
            select(SpeakingMetricsModel).where(
                SpeakingMetricsModel.speaking_response_id == response_id
            )
        )
        if not model:
            return None
        return SpeakingMetrics(
            id=model.id,
            speaking_response_id=model.speaking_response_id,
            pronunciation_score=model.pronunciation_score,
            accuracy_score=model.accuracy_score,
            fluency_score=model.fluency_score,
            completeness_score=model.completeness_score,
            prosody_score=model.prosody_score,
            raw_speech_result_json=model.raw_speech_result_json,
            raw_transcription_result_json=model.raw_transcription_result_json,
            comparison_json=model.comparison_json,
            review_json=model.review_json,
            quality_json=model.quality_json,
            original_pronunciation_score=model.original_pronunciation_score,
            current_pronunciation_score=model.current_pronunciation_score,
            original_accuracy_score=model.original_accuracy_score,
            current_accuracy_score=model.current_accuracy_score,
            original_fluency_score=model.original_fluency_score,
            current_fluency_score=model.current_fluency_score,
            original_completeness_score=model.original_completeness_score,
            current_completeness_score=model.current_completeness_score,
            original_lexical_match=model.original_lexical_match,
            current_lexical_match=model.current_lexical_match,
            original_prosody_score=model.original_prosody_score,
            current_prosody_score=model.current_prosody_score,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def update(self, m: SpeakingMetrics) -> SpeakingMetrics:
        model = self._db.get(SpeakingMetricsModel, m.id)
        if model:
            model.pronunciation_score = m.pronunciation_score
            model.accuracy_score = m.accuracy_score
            model.fluency_score = m.fluency_score
            model.completeness_score = m.completeness_score
            model.prosody_score = m.prosody_score
            model.raw_speech_result_json = m.raw_speech_result_json
            model.raw_transcription_result_json = m.raw_transcription_result_json
            model.comparison_json = m.comparison_json
            model.review_json = m.review_json
            model.quality_json = m.quality_json
            model.original_pronunciation_score = m.original_pronunciation_score
            model.current_pronunciation_score = m.current_pronunciation_score
            model.original_accuracy_score = m.original_accuracy_score
            model.current_accuracy_score = m.current_accuracy_score
            model.original_fluency_score = m.original_fluency_score
            model.current_fluency_score = m.current_fluency_score
            model.original_completeness_score = m.original_completeness_score
            model.current_completeness_score = m.current_completeness_score
            model.original_lexical_match = m.original_lexical_match
            model.current_lexical_match = m.current_lexical_match
            model.original_prosody_score = m.original_prosody_score
            model.current_prosody_score = m.current_prosody_score
            self._db.flush()
        return m


class SQLAlchemyWritingMetricsRepository(WritingMetricsRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, m: WritingMetrics) -> WritingMetrics:
        model = WritingMetricsModel(
            writing_response_id=m.writing_response_id,
            confidence_avg=m.confidence_avg,
            cer=m.cer,
            wer=m.wer,
            similarity_score=m.similarity_score,
            raw_ocr_result_json=m.raw_ocr_result_json,
            duration_ms=m.duration_ms,
            stroke_count=m.stroke_count,
            point_count=m.point_count,
            average_speed=m.average_speed,
            speed_variability=m.speed_variability,
            pause_count=m.pause_count,
            longest_pause_ms=m.longest_pause_ms,
            total_pause_time_ms=m.total_pause_time_ms,
            pressure_min=m.pressure_min,
            pressure_max=m.pressure_max,
            pressure_avg=m.pressure_avg,
            bounding_box_json=m.bounding_box_json,
            writing_area_usage=m.writing_area_usage,
            review_json=m.review_json,
            quality_json=m.quality_json,
            original_char_accuracy=m.original_char_accuracy,
            current_char_accuracy=m.current_char_accuracy,
            original_word_accuracy=m.original_word_accuracy,
            current_word_accuracy=m.current_word_accuracy,
            original_similarity_score=m.original_similarity_score,
            current_similarity_score=m.current_similarity_score,
        )
        self._db.add(model)
        self._db.flush()
        return m

    def find_by_writing_response_id(self, response_id: UUID) -> WritingMetrics | None:
        model = self._db.scalar(
            select(WritingMetricsModel).where(
                WritingMetricsModel.writing_response_id == response_id
            )
        )
        if not model:
            return None
        return WritingMetrics(
            id=model.id,
            writing_response_id=model.writing_response_id,
            confidence_avg=model.confidence_avg,
            cer=model.cer,
            wer=model.wer,
            similarity_score=model.similarity_score,
            raw_ocr_result_json=model.raw_ocr_result_json,
            duration_ms=model.duration_ms,
            stroke_count=model.stroke_count,
            point_count=model.point_count,
            average_speed=model.average_speed,
            speed_variability=model.speed_variability,
            pause_count=model.pause_count,
            longest_pause_ms=model.longest_pause_ms,
            total_pause_time_ms=model.total_pause_time_ms,
            pressure_min=model.pressure_min,
            pressure_max=model.pressure_max,
            pressure_avg=model.pressure_avg,
            bounding_box_json=model.bounding_box_json,
            writing_area_usage=model.writing_area_usage,
            review_json=model.review_json,
            quality_json=model.quality_json,
            original_char_accuracy=model.original_char_accuracy,
            current_char_accuracy=model.current_char_accuracy,
            original_word_accuracy=model.original_word_accuracy,
            current_word_accuracy=model.current_word_accuracy,
            original_similarity_score=model.original_similarity_score,
            current_similarity_score=model.current_similarity_score,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def update(self, m: WritingMetrics) -> WritingMetrics:
        model = self._db.get(WritingMetricsModel, m.id)
        if model:
            model.confidence_avg = m.confidence_avg
            model.cer = m.cer
            model.wer = m.wer
            model.similarity_score = m.similarity_score
            model.raw_ocr_result_json = m.raw_ocr_result_json
            model.duration_ms = m.duration_ms
            model.stroke_count = m.stroke_count
            model.point_count = m.point_count
            model.average_speed = m.average_speed
            model.speed_variability = m.speed_variability
            model.pause_count = m.pause_count
            model.longest_pause_ms = m.longest_pause_ms
            model.total_pause_time_ms = m.total_pause_time_ms
            model.pressure_min = m.pressure_min
            model.pressure_max = m.pressure_max
            model.pressure_avg = m.pressure_avg
            model.bounding_box_json = m.bounding_box_json
            model.writing_area_usage = m.writing_area_usage
            model.review_json = m.review_json
            model.quality_json = m.quality_json
            model.original_char_accuracy = m.original_char_accuracy
            model.current_char_accuracy = m.current_char_accuracy
            model.original_word_accuracy = m.original_word_accuracy
            model.current_word_accuracy = m.current_word_accuracy
            model.original_similarity_score = m.original_similarity_score
            model.current_similarity_score = m.current_similarity_score
            self._db.flush()
        return m


class SQLAlchemyAssessmentResultRepository(AssessmentResultRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_attempt_id(self, attempt_id: UUID) -> AssessmentResultDomain | None:
        model = self._db.scalar(
            select(AssessmentResultModel).where(
                AssessmentResultModel.assessment_attempt_id == attempt_id
            )
        )
        return self._to_domain(model) if model else None

    def create(self, r: AssessmentResultDomain) -> AssessmentResultDomain:
        model = AssessmentResultModel(
            assessment_attempt_id=r.assessment_attempt_id,
            final_score=r.final_score,
            max_score=r.max_score,
            mc_correct_count=r.mc_correct_count,
            os_correct_count=r.os_correct_count,
            speaking_completed_count=r.speaking_completed_count,
            writing_completed_count=r.writing_completed_count,
            intervention_level=r.intervention_level.value if r.intervention_level else None,
            speaking_average_score=r.speaking_average_score,
            speaking_review_required_count=r.speaking_review_required_count,
            total_exercises=r.total_exercises,
            evaluated_exercises=r.evaluated_exercises,
            pending_exercises=r.pending_exercises,
            writing_average_score=r.writing_average_score,
            writing_review_required_count=r.writing_review_required_count,
            score_denominator=r.score_denominator,
            scoring_snapshot_json=r.scoring_snapshot_json,
            original_final_score=r.original_final_score,
            current_final_score=r.current_final_score,
            original_scoring_snapshot_json=r.original_scoring_snapshot_json,
            current_scoring_snapshot_json=r.current_scoring_snapshot_json,
            generated_at=r.generated_at,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def update(self, r: AssessmentResultDomain) -> AssessmentResultDomain:
        model = self._db.get(AssessmentResultModel, r.id)
        if model:
            model.final_score = r.final_score
            model.max_score = r.max_score
            model.mc_correct_count = r.mc_correct_count
            model.os_correct_count = r.os_correct_count
            model.speaking_completed_count = r.speaking_completed_count
            model.writing_completed_count = r.writing_completed_count
            model.intervention_level = r.intervention_level.value if r.intervention_level else None
            model.speaking_average_score = r.speaking_average_score
            model.speaking_review_required_count = r.speaking_review_required_count
            model.total_exercises = r.total_exercises
            model.evaluated_exercises = r.evaluated_exercises
            model.pending_exercises = r.pending_exercises
            model.writing_average_score = r.writing_average_score
            model.writing_review_required_count = r.writing_review_required_count
            model.score_denominator = r.score_denominator
            model.scoring_snapshot_json = r.scoring_snapshot_json
            model.original_final_score = r.original_final_score
            model.current_final_score = r.current_final_score
            model.original_scoring_snapshot_json = r.original_scoring_snapshot_json
            model.current_scoring_snapshot_json = r.current_scoring_snapshot_json
            model.generated_at = r.generated_at
            self._db.flush()
            return self._to_domain(model)
        return r

    @staticmethod
    def _to_domain(model: AssessmentResultModel) -> AssessmentResultDomain:
        return AssessmentResultDomain(
            id=model.id,
            assessment_attempt_id=model.assessment_attempt_id,
            final_score=model.final_score,
            max_score=model.max_score,
            mc_correct_count=model.mc_correct_count,
            os_correct_count=model.os_correct_count,
            speaking_completed_count=model.speaking_completed_count,
            writing_completed_count=model.writing_completed_count,
            intervention_level=InterventionLevel(model.intervention_level) if model.intervention_level else None,
            generated_at=model.generated_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            speaking_average_score=model.speaking_average_score,
            speaking_review_required_count=model.speaking_review_required_count,
            total_exercises=model.total_exercises,
            evaluated_exercises=model.evaluated_exercises,
            pending_exercises=model.pending_exercises,
            writing_average_score=model.writing_average_score,
            writing_review_required_count=model.writing_review_required_count,
            score_denominator=model.score_denominator,
            scoring_snapshot_json=model.scoring_snapshot_json,
            original_final_score=model.original_final_score,
            current_final_score=model.current_final_score,
            original_scoring_snapshot_json=model.original_scoring_snapshot_json,
            current_scoring_snapshot_json=model.current_scoring_snapshot_json,
        )


class SQLAlchemyExerciseScoreRepository(ExerciseScoreRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_exercise_attempt_id(self, exercise_attempt_id: UUID) -> ExerciseScore | None:
        model = self._db.scalar(
            select(ExerciseScoreModel).where(
                ExerciseScoreModel.exercise_attempt_id == exercise_attempt_id
            )
        )
        return self._to_domain(model) if model else None

    def find_by_assessment_attempt_id(self, attempt_id: UUID) -> list[ExerciseScore]:
        models = self._db.scalars(
            select(ExerciseScoreModel)
            .join(
                ExerciseAttemptModel,
                ExerciseAttemptModel.id == ExerciseScoreModel.exercise_attempt_id,
            )
            .where(ExerciseAttemptModel.assessment_attempt_id == attempt_id)
        )
        return [self._to_domain(model) for model in models]

    def upsert(self, score: ExerciseScore) -> ExerciseScore:
        model = self._db.scalar(
            select(ExerciseScoreModel).where(
                ExerciseScoreModel.exercise_attempt_id == score.exercise_attempt_id
            )
        )
        if model is None:
            model = ExerciseScoreModel(exercise_attempt_id=score.exercise_attempt_id)
            self._db.add(model)
        model.exercise_type = score.exercise_type.value
        model.score = score.score
        model.score_eligible = score.score_eligible
        model.technical_status = score.technical_status.value
        model.manual_review_required = score.manual_review_required
        model.quality_reasons_json = score.quality_reasons
        model.scoring_components_json = score.scoring_components
        model.original_score = score.original_score
        model.current_score = score.current_score
        model.original_scoring_components_json = score.original_scoring_components
        model.current_scoring_components_json = score.current_scoring_components
        model.manual_adjustment_applied = score.manual_adjustment_applied
        model.review_status = score.review_status or self._default_review_status(score)
        model.metric_sources_json = score.metric_sources
        model.review_version = score.review_version
        model.teacher_observation = score.teacher_observation
        model.adjusted_by_teacher_id = score.adjusted_by_teacher_id
        model.adjusted_at = score.adjusted_at
        self._db.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: ExerciseScoreModel) -> ExerciseScore:
        return ExerciseScore(
            id=model.id,
            exercise_attempt_id=model.exercise_attempt_id,
            exercise_type=ExerciseType(model.exercise_type),
            score=model.score,
            score_eligible=model.score_eligible,
            technical_status=TechnicalStatus(model.technical_status),
            manual_review_required=model.manual_review_required,
            quality_reasons=list(model.quality_reasons_json or []),
            scoring_components=dict(model.scoring_components_json or {}),
            created_at=model.created_at,
            updated_at=model.updated_at,
            original_score=model.original_score,
            current_score=model.current_score,
            original_scoring_components=dict(model.original_scoring_components_json or {}),
            current_scoring_components=dict(model.current_scoring_components_json or {}),
            manual_adjustment_applied=model.manual_adjustment_applied,
            review_status=model.review_status,
            metric_sources=dict(model.metric_sources_json or {}) if model.metric_sources_json is not None else None,
            review_version=model.review_version,
            teacher_observation=model.teacher_observation,
            adjusted_by_teacher_id=model.adjusted_by_teacher_id,
            adjusted_at=model.adjusted_at,
        )

    @staticmethod
    def _default_review_status(score: ExerciseScore) -> str:
        if score.manual_adjustment_applied:
            return "overridden"
        if score.manual_review_required:
            return "pending"
        return "not_required"


class SQLAlchemyManualReviewEventRepository(ManualReviewEventRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, event: ManualReviewEvent) -> ManualReviewEvent:
        model = ManualReviewEventModel(
            exercise_attempt_id=event.exercise_attempt_id,
            assessment_attempt_id=event.assessment_attempt_id,
            teacher_id=event.teacher_id,
            review_version=event.review_version,
            action=event.action,
            teacher_observation=event.teacher_observation,
            before_state_json=event.before_state,
            after_state_json=event.after_state,
            corrections_json=event.corrections,
            manual_metrics_json=event.manual_metrics,
            metric_sources_json=event.metric_sources,
            evidence_version=event.evidence_version,
            base_review_version=event.base_review_version,
            created_at=event.created_at,
        )
        self._db.add(model)
        self._db.flush()
        return self._to_domain(model)

    def find_by_assessment_attempt_id(self, attempt_id: UUID) -> list[ManualReviewEvent]:
        models = self._db.scalars(
            select(ManualReviewEventModel)
            .where(ManualReviewEventModel.assessment_attempt_id == attempt_id)
            .order_by(ManualReviewEventModel.exercise_attempt_id, ManualReviewEventModel.review_version)
        )
        return [self._to_domain(model) for model in models]

    def find_by_exercise_attempt_id(self, exercise_attempt_id: UUID) -> list[ManualReviewEvent]:
        models = self._db.scalars(
            select(ManualReviewEventModel)
            .where(ManualReviewEventModel.exercise_attempt_id == exercise_attempt_id)
            .order_by(ManualReviewEventModel.review_version)
        )
        return [self._to_domain(model) for model in models]

    @staticmethod
    def _to_domain(model: ManualReviewEventModel) -> ManualReviewEvent:
        return ManualReviewEvent(
            id=model.id,
            exercise_attempt_id=model.exercise_attempt_id,
            assessment_attempt_id=model.assessment_attempt_id,
            teacher_id=model.teacher_id,
            review_version=model.review_version,
            action=model.action,
            teacher_observation=model.teacher_observation,
            before_state=dict(model.before_state_json or {}),
            after_state=dict(model.after_state_json or {}),
            corrections=dict(model.corrections_json or {}) if model.corrections_json is not None else None,
            manual_metrics=dict(model.manual_metrics_json or {}) if model.manual_metrics_json is not None else None,
            metric_sources=dict(model.metric_sources_json or {}) if model.metric_sources_json is not None else None,
            evidence_version=model.evidence_version,
            base_review_version=model.base_review_version,
            created_at=model.created_at,
        )
