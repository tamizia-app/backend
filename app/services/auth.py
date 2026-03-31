from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.teacher_profile import TeacherProfile
from app.models.user import User
from app.schemas.auth import MeResponse, TeacherProfileSummary, TokenResponse
from app.services.audit import create_audit_log


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user.")
    return user


def issue_tokens(db: Session, *, user: User, settings: Settings) -> TokenResponse:
    refresh_token = generate_refresh_token()
    refresh_hash = hash_refresh_token(refresh_token, settings)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
        )
    )

    access_token = create_access_token(subject=str(user.id), settings=settings, extra_claims={"role": user.role.value})
    expires_in = settings.access_token_expire_minutes * 60
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


def refresh_access_token(db: Session, *, refresh_token: str, settings: Settings) -> TokenResponse:
    token_hash = hash_refresh_token(refresh_token, settings)
    stored_token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    if not stored_token or stored_token.revoked_at is not None or stored_token.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

    user = db.get(User, stored_token.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user.")

    stored_token.revoked_at = datetime.now(UTC)
    return issue_tokens(db, user=user, settings=settings)


def revoke_refresh_token(db: Session, *, refresh_token: str, settings: Settings) -> None:
    token_hash = hash_refresh_token(refresh_token, settings)
    stored_token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if stored_token and stored_token.revoked_at is None:
        stored_token.revoked_at = datetime.now(UTC)


def build_me_response(user: User) -> MeResponse:
    teacher_profile = user.teacher_profile
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        teacher_profile=TeacherProfileSummary(
            id=teacher_profile.id,
            institution_name=teacher_profile.institution_name,
            phone=teacher_profile.phone,
        )
        if teacher_profile
        else None,
    )


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    institution_name: str | None,
    phone: str | None,
    role,
) -> User:
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    db.flush()
    db.add(
        TeacherProfile(
            user_id=user.id,
            institution_name=institution_name,
            phone=phone,
        )
    )
    create_audit_log(db, user=user, action="create_user", entity_type="user", entity_id=user.id)
    return user


def require_teacher_profile_id(user: User) -> UUID:
    if not user.teacher_profile:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher profile not configured.")
    return user.teacher_profile.id

