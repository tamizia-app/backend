from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ExerciseType
from app.models.exercise import Exercise


def list_exercises(db: Session, exercise_type: ExerciseType | None = None) -> list[Exercise]:
    query = select(Exercise).where(Exercise.is_active.is_(True))
    if exercise_type:
        query = query.where(Exercise.type == exercise_type)
    return list(db.scalars(query.order_by(Exercise.difficulty_level.asc(), Exercise.title.asc())))


def get_exercise(db: Session, exercise_id) -> Exercise:
    exercise = db.get(Exercise, exercise_id)
    if not exercise or not exercise.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found.")
    return exercise

