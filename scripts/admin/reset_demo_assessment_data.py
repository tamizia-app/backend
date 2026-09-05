from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.assessment.infrastructure.models.assessment_model import AssessmentModel
from app.assessment.infrastructure.models.attempt_model import (
    AssessmentAttemptModel,
    ExerciseAttemptModel,
)
from app.assessment.infrastructure.models.template_model import (
    AssessmentTemplateExerciseModel,
    AssessmentTemplateModel,
)
from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.school.infrastructure.models.classroom_model import ClassroomModel
from app.school.infrastructure.models.student_model import Student


@dataclass
class ResetPlanItem:
    template_id: UUID
    template_name: str
    template_version: int
    is_active: bool
    has_history: bool
    action: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safely reset demo assessment templates with an explicit dry-run first."
    )
    parser.add_argument("--confirm-reset-demo-data", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--teacher-id", type=UUID)
    parser.add_argument("--template-name-prefix")
    parser.add_argument("--student-name-prefix")
    parser.add_argument("--classroom-name-prefix")
    return parser


def has_template_history(db: Session, template_id: UUID) -> bool:
    assessment_id = db.scalar(
        select(AssessmentModel.id)
        .where(AssessmentModel.template_id == template_id)
        .limit(1)
    )
    if assessment_id:
        return True

    exercise_attempt_id = db.scalar(
        select(ExerciseAttemptModel.id)
        .join(
            AssessmentTemplateExerciseModel,
            ExerciseAttemptModel.template_exercise_id == AssessmentTemplateExerciseModel.id,
        )
        .where(AssessmentTemplateExerciseModel.template_id == template_id)
        .limit(1)
    )
    return bool(exercise_attempt_id)


def build_plan(db: Session, args: argparse.Namespace) -> list[ResetPlanItem]:
    query = select(AssessmentTemplateModel).distinct()
    joined_assessments = False

    if args.teacher_id:
        query = query.where(AssessmentTemplateModel.created_by_teacher_id == args.teacher_id)

    if args.template_name_prefix:
        query = query.where(AssessmentTemplateModel.name.startswith(args.template_name_prefix))

    if args.classroom_name_prefix:
        if not joined_assessments:
            query = query.join(AssessmentModel, AssessmentModel.template_id == AssessmentTemplateModel.id)
            joined_assessments = True
        query = (
            query.join(ClassroomModel, ClassroomModel.id == AssessmentModel.classroom_id)
            .where(ClassroomModel.name.startswith(args.classroom_name_prefix))
        )

    if args.student_name_prefix:
        if not joined_assessments:
            query = query.join(AssessmentModel, AssessmentModel.template_id == AssessmentTemplateModel.id)
            joined_assessments = True
        query = (
            query.join(AssessmentAttemptModel, AssessmentAttemptModel.assessment_id == AssessmentModel.id)
            .join(Student, Student.id == AssessmentAttemptModel.student_id)
            .where(Student.code.startswith(args.student_name_prefix))
        )

    templates = db.scalars(query.order_by(AssessmentTemplateModel.name)).all()
    plan: list[ResetPlanItem] = []
    for template in templates:
        has_history = has_template_history(db, template.id)
        if has_history and template.is_active:
            action = "deactivate"
        elif has_history:
            action = "report_inactive_with_history"
        else:
            action = "delete_template_without_history"
        plan.append(
            ResetPlanItem(
                template_id=template.id,
                template_name=template.name,
                template_version=template.version,
                is_active=template.is_active,
                has_history=has_history,
                action=action,
            )
        )
    return plan


def apply_plan(db: Session, plan: list[ResetPlanItem]) -> None:
    for item in plan:
        template = db.get(AssessmentTemplateModel, item.template_id)
        if not template:
            continue
        if item.action == "delete_template_without_history":
            db.query(AssessmentTemplateExerciseModel).filter(
                AssessmentTemplateExerciseModel.template_id == item.template_id
            ).delete()
            db.delete(template)
        elif item.action == "deactivate":
            template.is_active = False
    db.flush()


def has_any_filter(args: argparse.Namespace) -> bool:
    return bool(
        args.teacher_id
        or args.template_name_prefix
        or args.student_name_prefix
        or args.classroom_name_prefix
    )


def production_guard(settings: Settings) -> bool:
    return settings.environment == "production" and os.getenv("ALLOW_DEMO_DATA_RESET") != "true"


def print_plan(plan: list[ResetPlanItem], *, execute: bool) -> None:
    mode = "EXECUTE" if execute else "DRY-RUN"
    print(f"{mode}: {len(plan)} template(s) matched.")
    for item in plan:
        print(
            f"- {item.template_id} | {item.template_name} v{item.template_version} | "
            f"active={item.is_active} | history={item.has_history} | action={item.action}"
        )


def run(
    args: argparse.Namespace,
    *,
    session_factory=SessionLocal,
    settings: Settings | None = None,
) -> int:
    settings = settings or get_settings()

    if not args.confirm_reset_demo_data:
        print("Abort: pass --confirm-reset-demo-data to confirm this is demo data.")
        return 2

    if production_guard(settings):
        print("Abort: production requires ALLOW_DEMO_DATA_RESET=true.")
        return 2

    if not has_any_filter(args):
        print("Abort: pass at least one explicit filter before scanning demo data.")
        return 2

    with session_factory() as db:
        plan = build_plan(db, args)
        print_plan(plan, execute=args.execute)

        if args.execute:
            apply_plan(db, plan)
            db.commit()
            print("Done: reset demo assessment data plan applied.")
        else:
            db.rollback()
            print("Done: dry-run only, no data modified. Pass --execute to apply.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
