"""create IAM tables (users_iam, teachers_iam, refresh_tokens_iam)

Revision ID: 20260326_0002
Revises: 20260326_0001
Create Date: 2026-03-26 12:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "20260326_0002"
down_revision = "20260326_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users_iam",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("lastname", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users_iam")),
        sa.UniqueConstraint("email", name=op.f("uq_users_iam_email")),
    )
    op.create_index(op.f("ix_users_iam_email"), "users_iam", ["email"], unique=False)

    op.create_table(
        "teachers_iam",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("institute_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teachers_iam")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users_iam.id"],
            name=op.f("fk_teachers_iam_user_id_users_iam"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", name=op.f("uq_teachers_iam_user_id")),
        sa.UniqueConstraint("phone", name=op.f("uq_teachers_iam_phone")),
    )

    op.create_table(
        "refresh_tokens_iam",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens_iam")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users_iam.id"],
            name=op.f("fk_refresh_tokens_iam_user_id_users_iam"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_iam_token_hash")),
    )
    op.create_index(
        op.f("ix_refresh_tokens_iam_user_id"), "refresh_tokens_iam", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens_iam")
    op.drop_table("teachers_iam")
    op.drop_table("users_iam")
