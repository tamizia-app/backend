from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import ExerciseType
from app.schemas.exercise import ExerciseResponse
from app.services import exercises as exercise_service


router = APIRouter(prefix="/exercises")


@router.get("", response_model=list[ExerciseResponse])
def list_exercises(
    type: ExerciseType | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ExerciseResponse]:
    return exercise_service.list_exercises(db, exercise_type=type)


@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(exercise_id: UUID, db: Session = Depends(get_db)) -> ExerciseResponse:
    return exercise_service.get_exercise(db, exercise_id)

