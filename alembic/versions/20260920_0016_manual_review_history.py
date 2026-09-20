"""add manual review version and history

Revision ID: 20260920_0016
Revises: 20260920_0015
Create Date: 2026-09-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260920_0016"
down_revision = "20260920_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment_exercise_scores",
        sa.Column("review_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "assessment_exercise_manual_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("teacher_id", sa.Uuid(), nullable=True),
        sa.Column("review_version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("teacher_observation", sa.Text(), nullable=False),
        sa.Column("before_state_json", postgresql.JSON(), nullable=False),
        sa.Column("after_state_json", postgresql.JSON(), nullable=False),
        sa.Column("corrections_json", postgresql.JSON(), nullable=True),
        sa.Column("manual_metrics_json", postgresql.JSON(), nullable=True),
        sa.Column("metric_sources_json", postgresql.JSON(), nullable=True),
        sa.Column("evidence_version", sa.String(length=40), nullable=True),
        sa.Column("base_review_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_attempt_id"], ["assessment_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exercise_attempt_id"], ["assessment_exercise_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers_iam.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exercise_attempt_id", "review_version", name="uq_manual_review_exercise_version"),
    )
    op.create_index("ix_manual_reviews_exercise_attempt_id", "assessment_exercise_manual_reviews", ["exercise_attempt_id"])
    op.create_index("ix_manual_reviews_assessment_attempt_id", "assessment_exercise_manual_reviews", ["assessment_attempt_id"])
    op.create_index("ix_manual_reviews_created_at", "assessment_exercise_manual_reviews", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_manual_reviews_created_at", table_name="assessment_exercise_manual_reviews")
    op.drop_index("ix_manual_reviews_assessment_attempt_id", table_name="assessment_exercise_manual_reviews")
    op.drop_index("ix_manual_reviews_exercise_attempt_id", table_name="assessment_exercise_manual_reviews")
    op.drop_table("assessment_exercise_manual_reviews")
    op.drop_column("assessment_exercise_scores", "review_version")
