"""add manual review status

Revision ID: 20260920_0014
Revises: 20260915_0013
Create Date: 2026-09-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260920_0014"
down_revision = "20260915_0013"
branch_labels = None
depends_on = None


BACKFILL_REVIEW_STATUS_SQL = """
UPDATE assessment_exercise_scores
SET review_status = CASE
    WHEN manual_adjustment_applied = true THEN 'overridden'
    WHEN manual_review_required = true THEN 'pending'
    ELSE 'not_required'
END
"""


def upgrade() -> None:
    op.add_column(
        "assessment_exercise_scores",
        sa.Column(
            "review_status",
            sa.String(length=20),
            nullable=False,
            server_default="not_required",
        ),
    )
    op.execute(sa.text(BACKFILL_REVIEW_STATUS_SQL))


def downgrade() -> None:
    op.drop_column("assessment_exercise_scores", "review_status")
