from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.assessment.domain.enums import ExerciseType
from app.assessment.domain.exercise import AssessmentExercise
from app.assessment.domain.prompt import ExpectedAnswer, PromptExercise
from app.assessment.domain.question import MCAnswerOption, MCQuestion, OSAnswer, OSQuestion
from app.assessment.domain.template import AssessmentTemplate, AssessmentTemplateExercise
from app.assessment.infrastructure.models.exercise_model import AssessmentExerciseModel
from app.assessment.infrastructure.models.prompt_model import ExpectedAnswerModel, PromptExerciseModel
from app.assessment.infrastructure.models.question_model import (
    MCAnswerOptionModel,
    MCQuestionModel,
    OSAnswerModel,
    OSQuestionModel,
)
from app.assessment.infrastructure.models.template_model import AssessmentTemplateExerciseModel, AssessmentTemplateModel
from app.assessment.infrastructure.repositories.assessment_repositories import (
    SQLAlchemyExerciseRepository,
    SQLAlchemyMCAnswerOptionRepository,
    SQLAlchemyMCQuestionRepository,
    SQLAlchemyOSAnswerRepository,
    SQLAlchemyOSQuestionRepository,
    SQLAlchemyPromptExerciseRepository,
    SQLAlchemyExpectedAnswerRepository,
    SQLAlchemyTemplateExerciseRepository,
    SQLAlchemyTemplateRepository,
)
from app.db.session import SessionLocal

DEMO_TEMPLATE_NAME = "Demo Lectoescritura Básica"

MC_TITLE = "Comprensión simple - El gato"
OS_TITLE = "Ordena sílabas - casa"
SPEAKING_TITLE = "Lectura en voz alta - El gato"


def _get_or_create_template(db, template_repo, teacher_id):
    model = db.scalar(
        select(AssessmentTemplateModel).where(AssessmentTemplateModel.name == DEMO_TEMPLATE_NAME)
    )
    if model:
        tpl = template_repo._to_domain(model)
        print(f"  Template already exists: id={tpl.id}, name='{tpl.name}'")
        return tpl

    now = datetime.now(UTC)
    tpl = template_repo.create(
        AssessmentTemplate(
            id=UUID(int=0),
            name=DEMO_TEMPLATE_NAME,
            description="Template demo con ejercicios MC, OS y Speaking para pruebas rápidas.",
            version=1,
            is_active=True,
            created_by_teacher_id=teacher_id,
            created_at=now,
            updated_at=now,
        )
    )
    print(f"  Template created: id={tpl.id}, name='{tpl.name}'")
    return tpl


def _get_or_create_exercise(db, ex_repo, title):
    model = db.scalar(
        select(AssessmentExerciseModel).where(AssessmentExerciseModel.title == title)
    )
    if model:
        return ex_repo._to_domain(model)
    return None


def _create_mc_exercise(db, teacher_id):
    ex_repo = SQLAlchemyExerciseRepository(db)
    existing = _get_or_create_exercise(db, ex_repo, MC_TITLE)
    if existing:
        print(f"  MC exercise already exists: id={existing.id}, title='{existing.title}'")
        return existing

    now = datetime.now(UTC)
    mc_q_repo = SQLAlchemyMCQuestionRepository(db)
    mc_opt_repo = SQLAlchemyMCAnswerOptionRepository(db)

    exercise = ex_repo.create(
        AssessmentExercise(
            id=UUID(int=0),
            type=ExerciseType.MULTIPLE_CHOICE,
            title=MC_TITLE,
            instructions="Selecciona la respuesta correcta.",
            stimulus_type="text",
            response_type="option",
            difficulty_level=1,
            is_active=True,
            created_by_teacher_id=teacher_id,
            created_at=now,
            updated_at=now,
        )
    )

    mc_q = mc_q_repo.create(
        MCQuestion(
            id=UUID(int=0),
            exercise_id=exercise.id,
            question_text="¿Qué animal está en la casa?",
            image_blob_path=None,
            created_at=now,
            updated_at=now,
        )
    )

    for opt_data in [
        ("Gato", True, 1),
        ("Perro", False, 2),
        ("Pato", False, 3),
    ]:
        mc_opt_repo.create(
            MCAnswerOption(
                id=UUID(int=0),
                mc_question_id=mc_q.id,
                text=opt_data[0],
                is_correct=opt_data[1],
                order_index=opt_data[2],
                created_at=now,
                updated_at=now,
            )
        )

    print(f"  MC exercise created: id={exercise.id}, title='{exercise.title}'")
    return exercise


def _create_os_exercise(db, teacher_id):
    ex_repo = SQLAlchemyExerciseRepository(db)
    existing = _get_or_create_exercise(db, ex_repo, OS_TITLE)
    if existing:
        print(f"  OS exercise already exists: id={existing.id}, title='{existing.title}'")
        return existing

    now = datetime.now(UTC)
    os_q_repo = SQLAlchemyOSQuestionRepository(db)
    os_a_repo = SQLAlchemyOSAnswerRepository(db)

    exercise = ex_repo.create(
        AssessmentExercise(
            id=UUID(int=0),
            type=ExerciseType.ORDER_SYLLABLES,
            title=OS_TITLE,
            instructions="Ordena las sílabas para formar la palabra correcta.",
            stimulus_type="text",
            response_type="syllable_order",
            difficulty_level=1,
            is_active=True,
            created_by_teacher_id=teacher_id,
            created_at=now,
            updated_at=now,
        )
    )

    os_q = os_q_repo.create(
        OSQuestion(
            id=UUID(int=0),
            exercise_id=exercise.id,
            question_text="Ordena las sílabas para formar la palabra.",
            image_blob_path=None,
            created_at=now,
            updated_at=now,
        )
    )

    os_a_repo.create(
        OSAnswer(
            id=UUID(int=0),
            os_question_id=os_q.id,
            correct_word="casa",
            syllables_json=["sa", "ca"],
            created_at=now,
            updated_at=now,
        )
    )

    print(f"  OS exercise created: id={exercise.id}, title='{exercise.title}'")
    return exercise


def _create_speaking_exercise(db, teacher_id):
    ex_repo = SQLAlchemyExerciseRepository(db)
    existing = _get_or_create_exercise(db, ex_repo, SPEAKING_TITLE)
    if existing:
        print(f"  Speaking exercise already exists: id={existing.id}, title='{existing.title}'")
        return existing

    now = datetime.now(UTC)
    prompt_repo = SQLAlchemyPromptExerciseRepository(db)
    expected_repo = SQLAlchemyExpectedAnswerRepository(db)

    exercise = ex_repo.create(
        AssessmentExercise(
            id=UUID(int=0),
            type=ExerciseType.READING_SPEAKING,
            title=SPEAKING_TITLE,
            instructions="Lee en voz alta el texto que aparece en pantalla.",
            stimulus_type="text",
            response_type="audio",
            difficulty_level=1,
            is_active=True,
            created_by_teacher_id=teacher_id,
            created_at=now,
            updated_at=now,
        )
    )

    prompt = prompt_repo.create(
        PromptExercise(
            id=UUID(int=0),
            exercise_id=exercise.id,
            prompt_text=None,
            text_to_show="El gato está en la casa.",
            audio_blob_path=None,
            image_blob_path=None,
            language_code="es-PE",
            created_at=now,
            updated_at=now,
        )
    )

    expected_repo.create(
        ExpectedAnswer(
            id=UUID(int=0),
            prompt_exercise_id=prompt.id,
            expected_text="El gato está en la casa.",
            created_at=now,
            updated_at=now,
        )
    )

    print(f"  Speaking exercise created: id={exercise.id}, title='{exercise.title}'")
    return exercise


def _get_or_create_template_exercise(db, te_repo, template_id, exercise_id, order_index, points, is_required):
    models = db.scalars(
        select(AssessmentTemplateExerciseModel)
        .where(AssessmentTemplateExerciseModel.template_id == template_id)
        .where(AssessmentTemplateExerciseModel.exercise_id == exercise_id)
    ).all()
    if models:
        te = te_repo._to_domain(models[0])
        print(f"  TemplateExercise already exists: id={te.id}, exercise_id={exercise_id}")
        return

    now = datetime.now(UTC)
    te_repo.create(
        AssessmentTemplateExercise(
            id=UUID(int=0),
            template_id=template_id,
            exercise_id=exercise_id,
            order_index=order_index,
            points=points,
            is_required=is_required,
            created_at=now,
            updated_at=now,
        )
    )
    print(f"  TemplateExercise created: template_id={template_id}, exercise_id={exercise_id}")


def seed_demo(teacher_id: UUID | None = None, create_assessment: bool = False, classroom_id: UUID | None = None) -> None:
    db = SessionLocal()
    try:
        print("\n=== Seed Assessment Demo ===\n")

        template_repo = SQLAlchemyTemplateRepository(db)
        te_repo = SQLAlchemyTemplateExerciseRepository(db)

        if not teacher_id:
            from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
            teacher = db.scalar(select(HomeroomTeacherModel))
            if not teacher:
                print("ERROR: No teacher found in the database. Create a teacher first or pass --teacher-id.")
                return
            teacher_id = teacher.id
            print(f"  Using teacher: id={teacher_id}")

        print(f"\n1. Template")
        template = _get_or_create_template(db, template_repo, teacher_id)

        print(f"\n2. Exercises")
        mc_ex = _create_mc_exercise(db, teacher_id)
        os_ex = _create_os_exercise(db, teacher_id)
        sp_ex = _create_speaking_exercise(db, teacher_id)

        print(f"\n3. Template-Exercise associations")
        _get_or_create_template_exercise(db, te_repo, template.id, mc_ex.id, order_index=1, points=5, is_required=True)
        _get_or_create_template_exercise(db, te_repo, template.id, os_ex.id, order_index=2, points=5, is_required=True)
        _get_or_create_template_exercise(db, te_repo, template.id, sp_ex.id, order_index=3, points=5, is_required=True)

        db.commit()

        print(f"\n=== Summary ===")
        print(f"  template_id: {template.id}")
        print(f"  exercise_ids: [{mc_ex.id}, {os_ex.id}, {sp_ex.id}]")

        if create_assessment:
            if not classroom_id:
                from app.school.infrastructure.models.classroom_model import ClassroomModel
                classroom = db.scalar(select(ClassroomModel))
                if not classroom:
                    print("ERROR: --create-assessment requires --classroom-id or an existing classroom in DB.")
                    return
                classroom_id = classroom.id
                print(f"  Using classroom: id={classroom_id}")

            now = datetime.now(UTC)
            from app.assessment.domain.assessment import Assessment, AssessmentStatus
            from app.assessment.infrastructure.repositories.assessment_repositories import SQLAlchemyAssessmentRepository
            from app.assessment.infrastructure.models.assessment_model import AssessmentModel

            existing_assessment = db.scalar(
                select(AssessmentModel)
                .where(AssessmentModel.template_id == template.id)
                .where(AssessmentModel.classroom_id == classroom_id)
            )
            if existing_assessment:
                print(f"  Assessment already exists: id={existing_assessment.id}")
                print(f"\n  assessment_id: {existing_assessment.id}")
            else:
                ass_repo = SQLAlchemyAssessmentRepository(db)
                assessment = ass_repo.create(
                    Assessment(
                        id=UUID(int=0),
                        template_id=template.id,
                        classroom_id=classroom_id,
                        homeroom_teacher_id=teacher_id,
                        title=f"Demo - {DEMO_TEMPLATE_NAME}",
                        status=AssessmentStatus.ACTIVE,
                        scheduled_at=None,
                        created_at=now,
                        updated_at=now,
                    )
                )
                db.commit()
                print(f"\n  Assessment created: id={assessment.id}")
                print(f"  assessment_id: {assessment.id}")

        print("\nDone.")
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo assessment data (idempotent).")
    parser.add_argument("--teacher-id", type=UUID, help="Teacher UUID (uses first teacher if omitted)")
    parser.add_argument("--create-assessment", action="store_true", help="Also create a demo Assessment")
    parser.add_argument("--classroom-id", type=UUID, help="Classroom UUID (required with --create-assessment if no classroom exists)")
    args = parser.parse_args()

    seed_demo(
        teacher_id=args.teacher_id,
        create_assessment=args.create_assessment,
        classroom_id=args.classroom_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
