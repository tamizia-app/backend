from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentCreate, StudentUpdate
from app.services.audit import create_audit_log
from app.services.classrooms import get_classroom_for_user


def list_students_by_classroom(db: Session, *, classroom_id, current_user: User) -> list[Student]:
    classroom = get_classroom_for_user(db, classroom_id, current_user)
    query = select(Student).where(Student.classroom_id == classroom.id).order_by(Student.created_at.desc())
    return list(db.scalars(query))


def create_student(db: Session, *, classroom_id, current_user: User, payload: StudentCreate) -> Student:
    classroom = get_classroom_for_user(db, classroom_id, current_user)
    existing = db.scalar(
        select(Student).where(Student.classroom_id == classroom.id, Student.code == payload.code)
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student code already exists in classroom.")

    student = Student(classroom_id=classroom.id, **payload.model_dump())
    db.add(student)
    db.flush()
    create_audit_log(db, user=current_user, action="create_student", entity_type="student", entity_id=student.id)
    return student


def get_student_for_user(db: Session, student_id, current_user: User) -> Student:
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    get_classroom_for_user(db, student.classroom_id, current_user)
    return student


def update_student(db: Session, *, student: Student, current_user: User, payload: StudentUpdate) -> Student:
    if payload.code and payload.code != student.code:
        existing = db.scalar(
            select(Student).where(
                Student.classroom_id == student.classroom_id,
                Student.code == payload.code,
                Student.id != student.id,
            )
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student code already exists in classroom.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    db.flush()
    create_audit_log(db, user=current_user, action="update_student", entity_type="student", entity_id=student.id)
    return student

