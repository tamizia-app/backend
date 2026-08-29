"""add repeated_from_attempt_id and repeat_reason to assessment_attempts

Revision ID: 20260628_0010
Revises: 20260628_0009
Create Date: 2026-06-28 18:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260628_0010"
down_revision = "20260328_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assessment_attempts") as batch_op:
        batch_op.add_column(
            sa.Column("repeated_from_attempt_id", sa.Uuid(), nullable=True)
        )
        batch_op.add_column(sa.Column("repeat_reason", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_assessment_attempts_repeated_from_attempt_id_assessment_attempts",
            "assessment_attempts",
            ["repeated_from_attempt_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_assessment_attempts_repeated_from_attempt_id",
            ["repeated_from_attempt_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("assessment_attempts") as batch_op:
        batch_op.drop_index("ix_assessment_attempts_repeated_from_attempt_id")
        batch_op.drop_constraint(
            "fk_assessment_attempts_repeated_from_attempt_id_assessment_attempts",
            type_="foreignkey",
        )
        batch_op.drop_column("repeat_reason")
        batch_op.drop_column("repeated_from_attempt_id")
