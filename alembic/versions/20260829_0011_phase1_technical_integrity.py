"""phase 1 technical integrity and scoring traceability

Revision ID: 20260829_0011
Revises: 20260628_0010
Create Date: 2026-08-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260829_0011"
down_revision = "20260628_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessment_speaking_metrics", sa.Column("comparison_json", postgresql.JSON(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("review_json", postgresql.JSON(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("quality_json", postgresql.JSON(), nullable=True))
    op.add_column("assessment_writing_metrics", sa.Column("review_json", postgresql.JSON(), nullable=True))
    op.add_column("assessment_writing_metrics", sa.Column("quality_json", postgresql.JSON(), nullable=True))

    op.add_column("assessment_results", sa.Column("speaking_average_score", sa.Float(), nullable=True))
    op.add_column("assessment_results", sa.Column("speaking_review_required_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("assessment_results", sa.Column("total_exercises", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("assessment_results", sa.Column("evaluated_exercises", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("assessment_results", sa.Column("pending_exercises", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("assessment_results", sa.Column("writing_average_score", sa.Float(), nullable=True))
    op.add_column("assessment_results", sa.Column("writing_review_required_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("assessment_results", sa.Column("score_denominator", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("assessment_results", sa.Column("scoring_snapshot_json", postgresql.JSON(), nullable=True))

    op.create_table(
        "assessment_exercise_scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_type", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("score_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("technical_status", sa.String(length=20), nullable=False),
        sa.Column("manual_review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quality_reasons_json", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("scoring_components_json", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["exercise_attempt_id"], ["assessment_exercise_attempts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exercise_attempt_id"),
    )
    op.create_index("ix_assessment_exercise_scores_exercise_attempt_id", "assessment_exercise_scores", ["exercise_attempt_id"])

    # Existing results used max_score as 100 * number of exercises while
    # final_score was already a normalized 0-100 average. Normalize the scale
    # metadata without changing any stored final score or intervention level.
    op.execute(
        sa.text(
            "UPDATE assessment_results SET max_score = 100 "
            "WHERE final_score IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_assessment_exercise_scores_exercise_attempt_id", table_name="assessment_exercise_scores")
    op.drop_table("assessment_exercise_scores")
    for column in (
        "scoring_snapshot_json", "score_denominator", "writing_review_required_count",
        "writing_average_score", "pending_exercises", "evaluated_exercises", "total_exercises",
        "speaking_review_required_count", "speaking_average_score",
    ):
        op.drop_column("assessment_results", column)
    op.drop_column("assessment_writing_metrics", "quality_json")
    op.drop_column("assessment_writing_metrics", "review_json")
    op.drop_column("assessment_speaking_metrics", "quality_json")
    op.drop_column("assessment_speaking_metrics", "review_json")
    op.drop_column("assessment_speaking_metrics", "comparison_json")
