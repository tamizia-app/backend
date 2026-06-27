"""create assessment module tables

Revision ID: 20260326_0006
Revises: 20260326_0005
Create Date: 2026-03-26 20:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision = "20260326_0006"
down_revision = "20260326_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Definition tables ─────────────────────────────────────

    op.create_table(
        "assessment_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_teacher_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["created_by_teacher_id"],
            ["teachers_iam.id"],
            name=op.f("fk_assessment_templates_created_by_teacher_id_teachers_iam"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_templates")),
    )
    op.create_index(
        op.f("ix_assessment_templates_created_by_teacher_id"),
        "assessment_templates",
        ["created_by_teacher_id"],
        unique=False,
    )

    op.create_table(
        "assessment_exercises",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.String(length=1000), nullable=True),
        sa.Column("stimulus_type", sa.String(length=50), nullable=True),
        sa.Column("response_type", sa.String(length=50), nullable=True),
        sa.Column("difficulty_level", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_teacher_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["created_by_teacher_id"],
            ["teachers_iam.id"],
            name=op.f("fk_assessment_exercises_created_by_teacher_id_teachers_iam"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_exercises")),
    )
    op.create_index(op.f("ix_assessment_exercises_type"), "assessment_exercises", ["type"], unique=False)
    op.create_index(
        op.f("ix_assessment_exercises_created_by_teacher_id"),
        "assessment_exercises",
        ["created_by_teacher_id"],
        unique=False,
    )

    op.create_table(
        "assessment_os_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("question_text", sa.String(length=500), nullable=False),
        sa.Column("image_blob_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["assessment_exercises.id"],
            name=op.f("fk_assessment_os_questions_exercise_id_assessment_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_os_questions")),
        sa.UniqueConstraint("exercise_id", name=op.f("uq_assessment_os_questions_exercise_id")),
    )
    op.create_index(
        op.f("ix_assessment_os_questions_exercise_id"),
        "assessment_os_questions",
        ["exercise_id"],
        unique=True,
    )

    op.create_table(
        "assessment_os_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("os_question_id", sa.Uuid(), nullable=False),
        sa.Column("correct_word", sa.String(length=255), nullable=False),
        sa.Column("syllables_json", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["os_question_id"],
            ["assessment_os_questions.id"],
            name=op.f("fk_assessment_os_answers_os_question_id_assessment_os_questions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_os_answers")),
        sa.UniqueConstraint("os_question_id", name=op.f("uq_assessment_os_answers_os_question_id")),
    )
    op.create_index(
        op.f("ix_assessment_os_answers_os_question_id"),
        "assessment_os_answers",
        ["os_question_id"],
        unique=True,
    )

    op.create_table(
        "assessment_mc_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("question_text", sa.String(length=500), nullable=False),
        sa.Column("image_blob_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["assessment_exercises.id"],
            name=op.f("fk_assessment_mc_questions_exercise_id_assessment_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_mc_questions")),
        sa.UniqueConstraint("exercise_id", name=op.f("uq_assessment_mc_questions_exercise_id")),
    )
    op.create_index(
        op.f("ix_assessment_mc_questions_exercise_id"),
        "assessment_mc_questions",
        ["exercise_id"],
        unique=True,
    )

    op.create_table(
        "assessment_mc_answer_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mc_question_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(length=255), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["mc_question_id"],
            ["assessment_mc_questions.id"],
            name=op.f("fk_assessment_mc_answer_options_mc_question_id_assessment_mc_questions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_mc_answer_options")),
    )
    op.create_index(
        op.f("ix_assessment_mc_answer_options_mc_question_id"),
        "assessment_mc_answer_options",
        ["mc_question_id"],
        unique=False,
    )

    op.create_table(
        "assessment_prompt_exercises",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_text", sa.String(length=1000), nullable=True),
        sa.Column("text_to_show", sa.String(length=500), nullable=True),
        sa.Column("audio_blob_path", sa.String(length=500), nullable=True),
        sa.Column("image_blob_path", sa.String(length=500), nullable=True),
        sa.Column("language_code", sa.String(length=20), nullable=False, server_default="es-PE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["assessment_exercises.id"],
            name=op.f("fk_assessment_prompt_exercises_exercise_id_assessment_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_prompt_exercises")),
        sa.UniqueConstraint("exercise_id", name=op.f("uq_assessment_prompt_exercises_exercise_id")),
    )
    op.create_index(
        op.f("ix_assessment_prompt_exercises_exercise_id"),
        "assessment_prompt_exercises",
        ["exercise_id"],
        unique=True,
    )

    op.create_table(
        "assessment_expected_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("prompt_exercise_id", sa.Uuid(), nullable=False),
        sa.Column("expected_text", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["prompt_exercise_id"],
            ["assessment_prompt_exercises.id"],
            name=op.f("fk_assessment_expected_answers_prompt_exercise_id_assessment_prompt_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_expected_answers")),
        sa.UniqueConstraint(
            "prompt_exercise_id", name=op.f("uq_assessment_expected_answers_prompt_exercise_id")
        ),
    )
    op.create_index(
        op.f("ix_assessment_expected_answers_prompt_exercise_id"),
        "assessment_expected_answers",
        ["prompt_exercise_id"],
        unique=True,
    )

    op.create_table(
        "assessment_template_exercises",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["assessment_templates.id"],
            name=op.f("fk_assessment_template_exercises_template_id_assessment_templates"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["assessment_exercises.id"],
            name=op.f("fk_assessment_template_exercises_exercise_id_assessment_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_template_exercises")),
    )
    op.create_index(
        op.f("ix_assessment_template_exercises_template_id"),
        "assessment_template_exercises",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_template_exercises_exercise_id"),
        "assessment_template_exercises",
        ["exercise_id"],
        unique=False,
    )

    # ── Execution tables ─────────────────────────────────────

    op.create_table(
        "assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("homeroom_teacher_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("scheduled_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["assessment_templates.id"],
            name=op.f("fk_assessments_template_id_assessment_templates"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["classroom_id"],
            ["school_classrooms.id"],
            name=op.f("fk_assessments_classroom_id_school_classrooms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["homeroom_teacher_id"],
            ["teachers_iam.id"],
            name=op.f("fk_assessments_homeroom_teacher_id_teachers_iam"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessments")),
    )
    op.create_index(op.f("ix_assessments_template_id"), "assessments", ["template_id"], unique=False)
    op.create_index(op.f("ix_assessments_classroom_id"), "assessments", ["classroom_id"], unique=False)
    op.create_index(
        op.f("ix_assessments_homeroom_teacher_id"),
        "assessments",
        ["homeroom_teacher_id"],
        unique=False,
    )

    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            name=op.f("fk_assessment_attempts_assessment_id_assessments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_assessment_attempts_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_attempts")),
    )
    op.create_index(
        op.f("ix_assessment_attempts_assessment_id"),
        "assessment_attempts",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_attempts_student_id"),
        "assessment_attempts",
        ["student_id"],
        unique=False,
    )

    op.create_table(
        "assessment_exercise_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("template_exercise_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["assessment_attempt_id"],
            ["assessment_attempts.id"],
            name=op.f("fk_assessment_exercise_attempts_assessment_attempt_id_assessment_attempts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_exercise_id"],
            ["assessment_template_exercises.id"],
            name=op.f("fk_assessment_exercise_attempts_template_exercise_id_assessment_template_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_exercise_attempts")),
    )
    op.create_index(
        op.f("ix_assessment_exercise_attempts_assessment_attempt_id"),
        "assessment_exercise_attempts",
        ["assessment_attempt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_exercise_attempts_template_exercise_id"),
        "assessment_exercise_attempts",
        ["template_exercise_id"],
        unique=False,
    )

    op.create_table(
        "assessment_mc_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("selected_option_id", sa.Uuid(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["exercise_attempt_id"],
            ["assessment_exercise_attempts.id"],
            name=op.f("fk_assessment_mc_responses_exercise_attempt_id_assessment_exercise_attempts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["selected_option_id"],
            ["assessment_mc_answer_options.id"],
            name=op.f("fk_assessment_mc_responses_selected_option_id_assessment_mc_answer_options"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_mc_responses")),
        sa.UniqueConstraint(
            "exercise_attempt_id", name=op.f("uq_assessment_mc_responses_exercise_attempt_id")
        ),
    )
    op.create_index(
        op.f("ix_assessment_mc_responses_exercise_attempt_id"),
        "assessment_mc_responses",
        ["exercise_attempt_id"],
        unique=True,
    )

    op.create_table(
        "assessment_os_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("selected_syllables_json", JSON, nullable=False),
        sa.Column("formed_word", sa.String(length=255), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["exercise_attempt_id"],
            ["assessment_exercise_attempts.id"],
            name=op.f("fk_assessment_os_responses_exercise_attempt_id_assessment_exercise_attempts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_os_responses")),
        sa.UniqueConstraint(
            "exercise_attempt_id", name=op.f("uq_assessment_os_responses_exercise_attempt_id")
        ),
    )
    op.create_index(
        op.f("ix_assessment_os_responses_exercise_attempt_id"),
        "assessment_os_responses",
        ["exercise_attempt_id"],
        unique=True,
    )

    op.create_table(
        "assessment_speaking_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("audio_blob_path", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("recognized_text", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["exercise_attempt_id"],
            ["assessment_exercise_attempts.id"],
            name=op.f("fk_assessment_speaking_responses_exercise_attempt_id_assessment_exercise_attempts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_speaking_responses")),
        sa.UniqueConstraint(
            "exercise_attempt_id",
            name=op.f("uq_assessment_speaking_responses_exercise_attempt_id"),
        ),
    )
    op.create_index(
        op.f("ix_assessment_speaking_responses_exercise_attempt_id"),
        "assessment_speaking_responses",
        ["exercise_attempt_id"],
        unique=True,
    )

    op.create_table(
        "assessment_writing_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exercise_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("image_blob_path", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("recognized_text", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["exercise_attempt_id"],
            ["assessment_exercise_attempts.id"],
            name=op.f("fk_assessment_writing_responses_exercise_attempt_id_assessment_exercise_attempts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_writing_responses")),
        sa.UniqueConstraint(
            "exercise_attempt_id",
            name=op.f("uq_assessment_writing_responses_exercise_attempt_id"),
        ),
    )
    op.create_index(
        op.f("ix_assessment_writing_responses_exercise_attempt_id"),
        "assessment_writing_responses",
        ["exercise_attempt_id"],
        unique=True,
    )

    op.create_table(
        "assessment_speaking_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("speaking_response_id", sa.Uuid(), nullable=False),
        sa.Column("pronunciation_score", sa.Float(), nullable=True),
        sa.Column("accuracy_score", sa.Float(), nullable=True),
        sa.Column("fluency_score", sa.Float(), nullable=True),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("prosody_score", sa.Float(), nullable=True),
        sa.Column("raw_speech_result_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["speaking_response_id"],
            ["assessment_speaking_responses.id"],
            name=op.f("fk_assessment_speaking_metrics_speaking_response_id_assessment_speaking_responses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_speaking_metrics")),
        sa.UniqueConstraint(
            "speaking_response_id",
            name=op.f("uq_assessment_speaking_metrics_speaking_response_id"),
        ),
    )
    op.create_index(
        op.f("ix_assessment_speaking_metrics_speaking_response_id"),
        "assessment_speaking_metrics",
        ["speaking_response_id"],
        unique=True,
    )

    op.create_table(
        "assessment_writing_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("writing_response_id", sa.Uuid(), nullable=False),
        sa.Column("confidence_avg", sa.Float(), nullable=True),
        sa.Column("cer", sa.Float(), nullable=True),
        sa.Column("wer", sa.Float(), nullable=True),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("raw_ocr_result_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["writing_response_id"],
            ["assessment_writing_responses.id"],
            name=op.f("fk_assessment_writing_metrics_writing_response_id_assessment_writing_responses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_writing_metrics")),
        sa.UniqueConstraint(
            "writing_response_id",
            name=op.f("uq_assessment_writing_metrics_writing_response_id"),
        ),
    )
    op.create_index(
        op.f("ix_assessment_writing_metrics_writing_response_id"),
        "assessment_writing_metrics",
        ["writing_response_id"],
        unique=True,
    )

    op.create_table(
        "assessment_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("max_score", sa.Float(), nullable=True),
        sa.Column("mc_correct_count", sa.Integer(), nullable=True),
        sa.Column("os_correct_count", sa.Integer(), nullable=True),
        sa.Column("speaking_completed_count", sa.Integer(), nullable=True),
        sa.Column("writing_completed_count", sa.Integer(), nullable=True),
        sa.Column("intervention_level", sa.String(length=20), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["assessment_attempt_id"],
            ["assessment_attempts.id"],
            name=op.f("fk_assessment_results_assessment_attempt_id_assessment_attempts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_results")),
        sa.UniqueConstraint(
            "assessment_attempt_id",
            name=op.f("uq_assessment_results_assessment_attempt_id"),
        ),
    )
    op.create_index(
        op.f("ix_assessment_results_assessment_attempt_id"),
        "assessment_results",
        ["assessment_attempt_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("assessment_results")
    op.drop_table("assessment_writing_metrics")
    op.drop_table("assessment_speaking_metrics")
    op.drop_table("assessment_writing_responses")
    op.drop_table("assessment_speaking_responses")
    op.drop_table("assessment_os_responses")
    op.drop_table("assessment_mc_responses")
    op.drop_table("assessment_exercise_attempts")
    op.drop_table("assessment_attempts")
    op.drop_table("assessments")
    op.drop_table("assessment_template_exercises")
    op.drop_table("assessment_expected_answers")
    op.drop_table("assessment_prompt_exercises")
    op.drop_table("assessment_mc_answer_options")
    op.drop_table("assessment_mc_questions")
    op.drop_table("assessment_os_answers")
    op.drop_table("assessment_os_questions")
    op.drop_table("assessment_exercises")
    op.drop_table("assessment_templates")
