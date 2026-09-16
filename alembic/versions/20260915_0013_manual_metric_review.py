"""manual metric review original and current scores

Revision ID: 20260915_0013
Revises: 20260905_0012
Create Date: 2026-09-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260915_0013"
down_revision = "20260905_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessment_speaking_metrics", sa.Column("original_pronunciation_score", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("current_pronunciation_score", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("original_accuracy_score", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("current_accuracy_score", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("original_fluency_score", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("current_fluency_score", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("original_completeness_score", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("current_completeness_score", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("original_lexical_match", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("current_lexical_match", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("original_prosody_score", sa.Float(), nullable=True))
    op.add_column("assessment_speaking_metrics", sa.Column("current_prosody_score", sa.Float(), nullable=True))

    op.add_column("assessment_writing_metrics", sa.Column("original_char_accuracy", sa.Float(), nullable=True))
    op.add_column("assessment_writing_metrics", sa.Column("current_char_accuracy", sa.Float(), nullable=True))
    op.add_column("assessment_writing_metrics", sa.Column("original_word_accuracy", sa.Float(), nullable=True))
    op.add_column("assessment_writing_metrics", sa.Column("current_word_accuracy", sa.Float(), nullable=True))
    op.add_column("assessment_writing_metrics", sa.Column("original_similarity_score", sa.Float(), nullable=True))
    op.add_column("assessment_writing_metrics", sa.Column("current_similarity_score", sa.Float(), nullable=True))

    op.add_column("assessment_exercise_scores", sa.Column("original_score", sa.Float(), nullable=True))
    op.add_column("assessment_exercise_scores", sa.Column("current_score", sa.Float(), nullable=True))
    op.add_column("assessment_exercise_scores", sa.Column("original_scoring_components_json", postgresql.JSON(), nullable=True))
    op.add_column("assessment_exercise_scores", sa.Column("current_scoring_components_json", postgresql.JSON(), nullable=True))
    op.add_column(
        "assessment_exercise_scores",
        sa.Column("manual_adjustment_applied", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("assessment_exercise_scores", sa.Column("teacher_observation", sa.Text(), nullable=True))
    op.add_column("assessment_exercise_scores", sa.Column("adjusted_by_teacher_id", sa.Uuid(), nullable=True))
    op.add_column("assessment_exercise_scores", sa.Column("adjusted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_ex_scores_adjusted_teacher",
        "assessment_exercise_scores",
        "teachers_iam",
        ["adjusted_by_teacher_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("assessment_results", sa.Column("original_final_score", sa.Float(), nullable=True))
    op.add_column("assessment_results", sa.Column("current_final_score", sa.Float(), nullable=True))
    op.add_column("assessment_results", sa.Column("original_scoring_snapshot_json", postgresql.JSON(), nullable=True))
    op.add_column("assessment_results", sa.Column("current_scoring_snapshot_json", postgresql.JSON(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE assessment_speaking_metrics
            SET
                original_pronunciation_score = pronunciation_score,
                current_pronunciation_score = pronunciation_score,
                original_accuracy_score = accuracy_score,
                current_accuracy_score = accuracy_score,
                original_fluency_score = fluency_score,
                current_fluency_score = fluency_score,
                original_completeness_score = completeness_score,
                current_completeness_score = completeness_score,
                original_lexical_match = NULLIF(comparison_json ->> 'lexical_match_percentage', '')::double precision,
                current_lexical_match = NULLIF(comparison_json ->> 'lexical_match_percentage', '')::double precision,
                original_prosody_score = prosody_score,
                current_prosody_score = prosody_score
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE assessment_writing_metrics
            SET
                original_char_accuracy = CASE
                    WHEN cer IS NULL THEN NULL
                    ELSE round((GREATEST(0.0, 100.0 * (1.0 - cer)))::numeric, 2)::double precision
                END,
                current_char_accuracy = CASE
                    WHEN cer IS NULL THEN NULL
                    ELSE round((GREATEST(0.0, 100.0 * (1.0 - cer)))::numeric, 2)::double precision
                END,
                original_word_accuracy = CASE
                    WHEN wer IS NULL THEN NULL
                    ELSE round((GREATEST(0.0, 100.0 * (1.0 - wer)))::numeric, 2)::double precision
                END,
                current_word_accuracy = CASE
                    WHEN wer IS NULL THEN NULL
                    ELSE round((GREATEST(0.0, 100.0 * (1.0 - wer)))::numeric, 2)::double precision
                END,
                original_similarity_score = similarity_score,
                current_similarity_score = similarity_score
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE assessment_exercise_scores
            SET
                original_score = score,
                current_score = score,
                original_scoring_components_json = scoring_components_json,
                current_scoring_components_json = scoring_components_json,
                manual_adjustment_applied = false
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE assessment_results
            SET
                original_final_score = final_score,
                current_final_score = final_score,
                original_scoring_snapshot_json = scoring_snapshot_json,
                current_scoring_snapshot_json = scoring_snapshot_json
            """
        )
    )


def downgrade() -> None:
    op.drop_column("assessment_results", "current_scoring_snapshot_json")
    op.drop_column("assessment_results", "original_scoring_snapshot_json")
    op.drop_column("assessment_results", "current_final_score")
    op.drop_column("assessment_results", "original_final_score")

    op.drop_constraint(
        "fk_ex_scores_adjusted_teacher",
        "assessment_exercise_scores",
        type_="foreignkey",
    )
    op.drop_column("assessment_exercise_scores", "adjusted_at")
    op.drop_column("assessment_exercise_scores", "adjusted_by_teacher_id")
    op.drop_column("assessment_exercise_scores", "teacher_observation")
    op.drop_column("assessment_exercise_scores", "manual_adjustment_applied")
    op.drop_column("assessment_exercise_scores", "current_scoring_components_json")
    op.drop_column("assessment_exercise_scores", "original_scoring_components_json")
    op.drop_column("assessment_exercise_scores", "current_score")
    op.drop_column("assessment_exercise_scores", "original_score")

    for column in (
        "current_similarity_score",
        "original_similarity_score",
        "current_word_accuracy",
        "original_word_accuracy",
        "current_char_accuracy",
        "original_char_accuracy",
    ):
        op.drop_column("assessment_writing_metrics", column)

    for column in (
        "current_prosody_score",
        "original_prosody_score",
        "current_lexical_match",
        "original_lexical_match",
        "current_completeness_score",
        "original_completeness_score",
        "current_fluency_score",
        "original_fluency_score",
        "current_accuracy_score",
        "original_accuracy_score",
        "current_pronunciation_score",
        "original_pronunciation_score",
    ):
        op.drop_column("assessment_speaking_metrics", column)
