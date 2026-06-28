"""add strokes_json and frontend metrics to writing responses

Revision ID: 20260328_0008
Revises: 20260326_0007
Create Date: 2026-06-28 10:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision = "20260328_0008"
down_revision = "20260326_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── assessment_writing_responses ───────────────────────────
    op.add_column(
        "assessment_writing_responses",
        sa.Column("strokes_json", JSON, nullable=True),
    )
    op.add_column(
        "assessment_writing_responses",
        sa.Column("canvas_metadata_json", JSON, nullable=True),
    )
    op.add_column(
        "assessment_writing_responses",
        sa.Column("input_metadata_json", JSON, nullable=True),
    )
    op.add_column(
        "assessment_writing_responses",
        sa.Column("frontend_metrics_json", JSON, nullable=True),
    )

    # ── assessment_writing_metrics ─────────────────────────────
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("stroke_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("point_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("average_speed", sa.Float(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("speed_variability", sa.Float(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("pause_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("longest_pause_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("total_pause_time_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("pressure_min", sa.Float(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("pressure_max", sa.Float(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("pressure_avg", sa.Float(), nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("bounding_box_json", JSON, nullable=True),
    )
    op.add_column(
        "assessment_writing_metrics",
        sa.Column("writing_area_usage", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    # ── assessment_writing_metrics ─────────────────────────────
    op.drop_column("assessment_writing_metrics", "writing_area_usage")
    op.drop_column("assessment_writing_metrics", "bounding_box_json")
    op.drop_column("assessment_writing_metrics", "pressure_avg")
    op.drop_column("assessment_writing_metrics", "pressure_max")
    op.drop_column("assessment_writing_metrics", "pressure_min")
    op.drop_column("assessment_writing_metrics", "total_pause_time_ms")
    op.drop_column("assessment_writing_metrics", "longest_pause_ms")
    op.drop_column("assessment_writing_metrics", "pause_count")
    op.drop_column("assessment_writing_metrics", "speed_variability")
    op.drop_column("assessment_writing_metrics", "average_speed")
    op.drop_column("assessment_writing_metrics", "point_count")
    op.drop_column("assessment_writing_metrics", "stroke_count")
    op.drop_column("assessment_writing_metrics", "duration_ms")

    # ── assessment_writing_responses ───────────────────────────
    op.drop_column("assessment_writing_responses", "frontend_metrics_json")
    op.drop_column("assessment_writing_responses", "input_metadata_json")
    op.drop_column("assessment_writing_responses", "canvas_metadata_json")
    op.drop_column("assessment_writing_responses", "strokes_json")
