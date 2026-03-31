from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.classroom import ClassroomCreate, ClassroomResponse, ClassroomUpdate
from app.schemas.student import StudentCreate, StudentResponse
from app.services import classrooms as classroom_service
from app.services import students as student_service


router = APIRouter(prefix="/classrooms")


@router.get("", response_model=list[ClassroomResponse])
def list_classrooms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[ClassroomResponse]:
    return classroom_service.list_classrooms(db, current_user)


@router.post("", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
def create_classroom(
    payload: ClassroomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClassroomResponse:
    classroom = classroom_service.create_classroom(db, current_user, payload)
    db.commit()
    db.refresh(classroom)
    return classroom


@router.get("/{classroom_id}", response_model=ClassroomResponse)
def get_classroom(classroom_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ClassroomResponse:
    return classroom_service.get_classroom_for_user(db, classroom_id, current_user)


@router.patch("/{classroom_id}", response_model=ClassroomResponse)
def update_classroom(
    classroom_id: UUID,
    payload: ClassroomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClassroomResponse:
    classroom = classroom_service.get_classroom_for_user(db, classroom_id, current_user)
    classroom = classroom_service.update_classroom(db, classroom, payload, current_user)
    db.commit()
    db.refresh(classroom)
    return classroom


@router.get("/{classroom_id}/students", response_model=list[StudentResponse])
def list_students_by_classroom(
    classroom_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentResponse]:
    return student_service.list_students_by_classroom(db, classroom_id=classroom_id, current_user=current_user)


@router.post("/{classroom_id}/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    classroom_id: UUID,
    payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentResponse:
    student = student_service.create_student(db, classroom_id=classroom_id, current_user=current_user, payload=payload)
    db.commit()
    db.refresh(student)
    return student

