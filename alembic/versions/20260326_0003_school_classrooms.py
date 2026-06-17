"""create school_classrooms table

Revision ID: 20260326_0003
Revises: 20260326_0002
Create Date: 2026-03-26 14:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0003"
down_revision = "20260326_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "school_classrooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("homeroom_teacher_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("grade_level", sa.String(length=20), nullable=False),
        sa.Column("section", sa.String(length=1), nullable=False),
        sa.Column("school_year", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_school_classrooms")),
        sa.ForeignKeyConstraint(
            ["homeroom_teacher_id"],
            ["teachers_iam.id"],
            name=op.f("fk_school_classrooms_homeroom_teacher_id_teachers_iam"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_school_classrooms_homeroom_teacher_id"),
        "school_classrooms",
        ["homeroom_teacher_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_school_classrooms_homeroom_teacher_id"), table_name="school_classrooms")
    op.drop_table("school_classrooms")
