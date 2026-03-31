from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import UserRole
from app.models.classroom import Classroom
from app.models.user import User
from app.schemas.classroom import ClassroomCreate, ClassroomUpdate
from app.services.audit import create_audit_log
from app.services.auth import require_teacher_profile_id


def list_classrooms(db: Session, current_user: User) -> list[Classroom]:
    query = select(Classroom)
    if current_user.role != UserRole.ADMIN:
        teacher_profile_id = require_teacher_profile_id(current_user)
        query = query.where(Classroom.teacher_profile_id == teacher_profile_id)
    return list(db.scalars(query.order_by(Classroom.created_at.desc())))


def create_classroom(db: Session, current_user: User, payload: ClassroomCreate) -> Classroom:
    classroom = Classroom(
        teacher_profile_id=require_teacher_profile_id(current_user),
        name=payload.name,
        grade_level=payload.grade_level,
        section=payload.section,
        school_year=payload.school_year,
    )
    db.add(classroom)
    db.flush()
    create_audit_log(db, user=current_user, action="create_classroom", entity_type="classroom", entity_id=classroom.id)
    return classroom


def get_classroom_for_user(db: Session, classroom_id, current_user: User) -> Classroom:
    classroom = db.get(Classroom, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found.")
    if current_user.role != UserRole.ADMIN and classroom.teacher_profile_id != require_teacher_profile_id(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found.")
    return classroom


def update_classroom(db: Session, classroom: Classroom, payload: ClassroomUpdate, current_user: User) -> Classroom:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(classroom, field, value)
    db.flush()
    create_audit_log(db, user=current_user, action="update_classroom", entity_type="classroom", entity_id=classroom.id)
    return classroom

