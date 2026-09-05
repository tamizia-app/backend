"""phase 2 scoring points default

Revision ID: 20260905_0012
Revises: 20260829_0011
Create Date: 2026-09-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260905_0012"
down_revision = "20260829_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New API writes validate points in {1, 2, 3}. Legacy rows are not rewritten
    # here, because pilots should correct old templates explicitly before use.
    op.alter_column(
        "assessment_template_exercises",
        "points",
        existing_type=sa.Integer(),
        server_default=sa.text("2"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "assessment_template_exercises",
        "points",
        existing_type=sa.Integer(),
        server_default=sa.text("10"),
        existing_nullable=False,
    )
