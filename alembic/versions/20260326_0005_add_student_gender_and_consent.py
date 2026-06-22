"""add student gender and student_consents table

Revision ID: 20260326_0005
Revises: 20260326_0004
Create Date: 2026-03-26 18:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0005"
down_revision = "20260326_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("gender", sa.String(length=10), nullable=False, server_default="BOY"),
    )
    op.drop_column("students", "first_name")
    op.drop_column("students", "last_name")
    op.drop_constraint("fk_students_classroom_id_classrooms", "students", type_="foreignkey")
    op.create_foreign_key(
        op.f("fk_students_classroom_id_school_classrooms"),
        "students",
        "school_classrooms",
        ["classroom_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_table(
        "student_consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_blob_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_consents")),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_student_consents_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("student_id", name=op.f("uq_student_consents_student_id")),
    )
    op.create_index(
        op.f("ix_student_consents_student_id"),
        "student_consents",
        ["student_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_student_consents_student_id"), table_name="student_consents")
    op.drop_table("student_consents")
    op.drop_constraint("fk_students_classroom_id_school_classrooms", "students", type_="foreignkey")
    op.create_foreign_key(
        "fk_students_classroom_id_classrooms",
        "students",
        "classrooms",
        ["classroom_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.add_column("students", sa.Column("last_name", sa.String(length=120), nullable=False, server_default=""))
    op.add_column("students", sa.Column("first_name", sa.String(length=120), nullable=False, server_default=""))
    op.drop_column("students", "gender")
