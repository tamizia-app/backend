from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LogoutRequest, MeResponse, RefreshRequest, TokenResponse
from app.schemas.common import MessageResponse
from app.services import auth as auth_service
from app.services.audit import create_audit_log


router = APIRouter(prefix="/auth")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> TokenResponse:
    user = auth_service.authenticate_user(db, email=payload.email, password=payload.password)
    tokens = auth_service.issue_tokens(db, user=user, settings=settings)
    create_audit_log(db, user=user, action="login", entity_type="auth", metadata={"email": user.email})
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> TokenResponse:
    tokens = auth_service.refresh_access_token(db, refresh_token=payload.refresh_token, settings=settings)
    db.commit()
    return tokens


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> MessageResponse:
    auth_service.revoke_refresh_token(db, refresh_token=payload.refresh_token, settings=settings)
    db.commit()
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return auth_service.build_me_response(current_user)
