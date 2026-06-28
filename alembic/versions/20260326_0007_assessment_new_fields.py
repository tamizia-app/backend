"""add free_transcription_text, assessment_recognized_text, raw_transcription_result_json

Revision ID: 20260326_0007
Revises: 20260326_0006
Create Date: 2026-06-27 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision = "20260326_0007"
down_revision = "20260326_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment_speaking_responses",
        sa.Column("free_transcription_text", sa.String(2000), nullable=True),
    )
    op.add_column(
        "assessment_speaking_responses",
        sa.Column("assessment_recognized_text", sa.String(2000), nullable=True),
    )
    op.add_column(
        "assessment_speaking_metrics",
        sa.Column("raw_transcription_result_json", JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_speaking_metrics", "raw_transcription_result_json")
    op.drop_column("assessment_speaking_responses", "assessment_recognized_text")
    op.drop_column("assessment_speaking_responses", "free_transcription_text")
