from __future__ import annotations

import argparse
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

from app.assessment.infrastructure.models.template_model import AssessmentTemplateModel
from app.db.session import SessionLocal


@dataclass
class MarkGlobalPlanItem:
    template_id: UUID
    name: str
    version: int
    is_active: bool
    previous_created_by_teacher_id: UUID | None
    new_created_by_teacher_id: None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mark existing assessment templates as global/official by exact template name."
    )
    parser.add_argument(
        "--template-name",
        action="append",
        default=[],
        help="Exact template name to mark global. Pass once per template.",
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-mark-global", action="store_true")
    return parser


def build_plan(db: Session, template_names: Sequence[str]) -> list[MarkGlobalPlanItem]:
    rows = db.scalars(
        select(AssessmentTemplateModel)
        .where(AssessmentTemplateModel.name.in_(template_names))
        .order_by(AssessmentTemplateModel.name, AssessmentTemplateModel.version)
    ).all()
    requested = set(template_names)
    return [
        MarkGlobalPlanItem(
            template_id=row.id,
            name=row.name,
            version=row.version,
            is_active=row.is_active,
            previous_created_by_teacher_id=row.created_by_teacher_id,
        )
        for row in rows
        if row.name in requested
    ]


def apply_plan(db: Session, plan: list[MarkGlobalPlanItem]) -> None:
    for item in plan:
        template = db.get(AssessmentTemplateModel, item.template_id)
        if template:
            template.created_by_teacher_id = None
    db.flush()


def print_plan(plan: list[MarkGlobalPlanItem], *, execute: bool) -> None:
    mode = "EXECUTE" if execute else "DRY-RUN"
    print(f"{mode}: {len(plan)} template(s) matched for global marking.")
    for item in plan:
        print(
            f"- template_id={item.template_id} | name={item.name} | version={item.version} | "
            f"is_active={item.is_active} | previous_created_by_teacher_id="
            f"{item.previous_created_by_teacher_id} | new_created_by_teacher_id=NULL"
        )


def run(args: argparse.Namespace, *, session_factory=SessionLocal) -> int:
    template_names = [name for name in args.template_name if name]
    if not template_names:
        print("Abort: pass at least one --template-name with an exact template name.")
        return 2

    if args.execute and not args.confirm_mark_global:
        print("Abort: pass --confirm-mark-global with --execute.")
        return 2

    with session_factory() as db:
        plan = build_plan(db, template_names)
        print_plan(plan, execute=args.execute)

        if args.execute:
            apply_plan(db, plan)
            db.commit()
            print("Done: selected existing templates were marked global.")
        else:
            db.rollback()
            print("Done: dry-run only, no data modified. Pass --execute --confirm-mark-global to apply.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
