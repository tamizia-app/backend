"""initial schema

Revision ID: 20260326_0001
Revises:
Create Date: 2026-03-26 10:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "20260326_0001"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = sa.Enum("teacher", "admin", name="userrole")
exercise_type_enum = sa.Enum("writing", "reading", "combined", name="exercisetype")
session_status_enum = sa.Enum("pending", "in_progress", "completed", "failed", "cancelled", name="sessionstatus")
risk_flag_enum = sa.Enum("LOW", "MEDIUM", "HIGH_REVIEW", name="riskflag")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "teacher_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("institution_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_teacher_profiles_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teacher_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_teacher_profiles_user_id")),
    )

    op.create_table(
        "classrooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("teacher_profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("grade_level", sa.String(length=50), nullable=False),
        sa.Column("section", sa.String(length=50), nullable=True),
        sa.Column("school_year", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["teacher_profile_id"],
            ["teacher_profiles.id"],
            name=op.f("fk_classrooms_teacher_profile_id_teacher_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classrooms")),
    )
    op.create_index(op.f("ix_classrooms_teacher_profile_id"), "classrooms", ["teacher_profile_id"], unique=False)

    op.create_table(
        "students",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], name=op.f("fk_students_classroom_id_classrooms"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
        sa.UniqueConstraint("classroom_id", "code", name="uq_students_classroom_code"),
    )
    op.create_index(op.f("ix_students_classroom_id"), "students", ["classroom_id"], unique=False)

    op.create_table(
        "exercises",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", exercise_type_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("reference_text", sa.Text(), nullable=False),
        sa.Column("difficulty_level", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercises")),
    )
    op.create_index(op.f("ix_exercises_type"), "exercises", ["type"], unique=False)

    op.create_table(
        "assessment_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("teacher_profile_id", sa.Uuid(), nullable=False),
        sa.Column("status", session_status_enum, nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], name=op.f("fk_assessment_sessions_exercise_id_exercises")),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], name=op.f("fk_assessment_sessions_student_id_students"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["teacher_profile_id"],
            ["teacher_profiles.id"],
            name=op.f("fk_assessment_sessions_teacher_profile_id_teacher_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_sessions")),
    )
    op.create_index(op.f("ix_assessment_sessions_status"), "assessment_sessions", ["status"], unique=False)
    op.create_index(op.f("ix_assessment_sessions_student_id"), "assessment_sessions", ["student_id"], unique=False)
    op.create_index(op.f("ix_assessment_sessions_teacher_profile_id"), "assessment_sessions", ["teacher_profile_id"], unique=False)

    op.create_table(
        "writing_samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("stroke_count", sa.Integer(), nullable=True),
        sa.Column("correction_count", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["assessment_sessions.id"], name=op.f("fk_writing_samples_session_id_assessment_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_writing_samples")),
        sa.UniqueConstraint("session_id", name=op.f("uq_writing_samples_session_id")),
    )

    op.create_table(
        "audio_samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("audio_url", sa.String(length=500), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("locale", sa.String(length=20), nullable=False, server_default="es-CO"),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["assessment_sessions.id"], name=op.f("fk_audio_samples_session_id_assessment_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audio_samples")),
        sa.UniqueConstraint("session_id", name=op.f("uq_audio_samples_session_id")),
    )

    op.create_table(
        "ocr_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("writing_sample_id", sa.Uuid(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence_avg", sa.Float(), nullable=True),
        sa.Column("cer_score", sa.Float(), nullable=True),
        sa.Column("wer_score", sa.Float(), nullable=True),
        sa.Column("omissions", sa.Integer(), nullable=True),
        sa.Column("substitutions", sa.Integer(), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["writing_sample_id"], ["writing_samples.id"], name=op.f("fk_ocr_analyses_writing_sample_id_writing_samples"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ocr_analyses")),
        sa.UniqueConstraint("writing_sample_id", name=op.f("uq_ocr_analyses_writing_sample_id")),
    )

    op.create_table(
        "pronunciation_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audio_sample_id", sa.Uuid(), nullable=False),
        sa.Column("accuracy_score", sa.Float(), nullable=True),
        sa.Column("fluency_score", sa.Float(), nullable=True),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("pronunciation_score", sa.Float(), nullable=True),
        sa.Column("recognized_text", sa.Text(), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["audio_sample_id"], ["audio_samples.id"], name=op.f("fk_pronunciation_analyses_audio_sample_id_audio_samples"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pronunciation_analyses")),
        sa.UniqueConstraint("audio_sample_id", name=op.f("uq_pronunciation_analyses_audio_sample_id")),
    )

    op.create_table(
        "session_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("writing_score", sa.Float(), nullable=True),
        sa.Column("reading_score", sa.Float(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("risk_flag", risk_flag_enum, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["assessment_sessions.id"], name=op.f("fk_session_results_session_id_assessment_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_results")),
        sa.UniqueConstraint("session_id", name=op.f("uq_session_results_session_id")),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_refresh_tokens_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_audit_logs_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)

    now = datetime.now(timezone.utc)
    exercises_table = sa.table(
        "exercises",
        sa.column("id", sa.Uuid()),
        sa.column("type", exercise_type_enum),
        sa.column("title", sa.String()),
        sa.column("instructions", sa.Text()),
        sa.column("reference_text", sa.Text()),
        sa.column("difficulty_level", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        exercises_table,
        [
            {
                "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
                "type": "writing",
                "title": "Copia de frase corta",
                "instructions": "Pide al estudiante copiar la frase exactamente como aparece.",
                "reference_text": "Mi casa tiene una ventana azul.",
                "difficulty_level": 1,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
                "type": "reading",
                "title": "Lectura en voz alta de frase corta",
                "instructions": "Pide al estudiante leer la frase en voz alta de forma natural.",
                "reference_text": "El perro corre por el patio.",
                "difficulty_level": 1,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
                "type": "combined",
                "title": "Lectura y copia guiada",
                "instructions": "Pide al estudiante leer la oración y luego escribirla.",
                "reference_text": "La luna brilla sobre el lago tranquilo.",
                "difficulty_level": 2,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("session_results")
    op.drop_table("pronunciation_analyses")
    op.drop_table("ocr_analyses")
    op.drop_table("audio_samples")
    op.drop_table("writing_samples")
    op.drop_index(op.f("ix_assessment_sessions_teacher_profile_id"), table_name="assessment_sessions")
    op.drop_index(op.f("ix_assessment_sessions_student_id"), table_name="assessment_sessions")
    op.drop_index(op.f("ix_assessment_sessions_status"), table_name="assessment_sessions")
    op.drop_table("assessment_sessions")
    op.drop_index(op.f("ix_exercises_type"), table_name="exercises")
    op.drop_table("exercises")
    op.drop_index(op.f("ix_students_classroom_id"), table_name="students")
    op.drop_table("students")
    op.drop_index(op.f("ix_classrooms_teacher_profile_id"), table_name="classrooms")
    op.drop_table("classrooms")
    op.drop_table("teacher_profiles")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
