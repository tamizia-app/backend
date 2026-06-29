"""add repeated_from_attempt_id and repeat_reason to assessment_attempts

Revision ID: 20260628_0010
Revises: 20260628_0009
Create Date: 2026-06-28 18:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260628_0010"
down_revision = "20260628_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment_attempts",
        sa.Column(
            "repeated_from_attempt_id",
            sa.Uuid(),
            sa.ForeignKey("assessment_attempts.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    op.add_column(
        "assessment_attempts",
        sa.Column("repeat_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_attempts", "repeat_reason")
    op.drop_column("assessment_attempts", "repeated_from_attempt_id")
