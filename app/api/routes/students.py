from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.session import SessionResponse
from app.schemas.student import StudentResponse, StudentUpdate
from app.services import sessions as session_service
from app.services import students as student_service


router = APIRouter(prefix="/students")


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> StudentResponse:
    return student_service.get_student_for_user(db, student_id, current_user)


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentResponse:
    student = student_service.get_student_for_user(db, student_id, current_user)
    student = student_service.update_student(db, student=student, current_user=current_user, payload=payload)
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}/sessions", response_model=list[SessionResponse])
def list_sessions_by_student(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SessionResponse]:
    return session_service.list_sessions_by_student(db, student_id=student_id, current_user=current_user)

