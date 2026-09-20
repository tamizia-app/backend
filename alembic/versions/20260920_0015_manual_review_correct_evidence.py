"""add reviewed evidence fields and metric sources

Revision ID: 20260920_0015
Revises: 20260920_0014
Create Date: 2026-09-20
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260920_0015"
down_revision = "20260920_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment_writing_responses",
        sa.Column("reviewed_recognized_text", sa.String(length=2000), nullable=True),
    )
    op.add_column(
        "assessment_speaking_responses",
        sa.Column("reviewed_free_transcription_text", sa.String(length=2000), nullable=True),
    )
    op.add_column(
        "assessment_exercise_scores",
        sa.Column("metric_sources_json", postgresql.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_exercise_scores", "metric_sources_json")
    op.drop_column("assessment_speaking_responses", "reviewed_free_transcription_text")
    op.drop_column("assessment_writing_responses", "reviewed_recognized_text")
