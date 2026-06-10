from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.iam.application.assemblers.auth_assembler import AuthAssembler
from app.iam.application.ports.repositories import (
    RefreshTokenRepository,
    TeacherRepository,
    UserRepository,
)
from app.iam.application.services.teacher_command_service import (
    TeacherCommandServiceImpl,
)
from app.iam.application.services.user_command_service import (
    UserCommandServiceImpl,
)
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.iam.infrastructure.repositories.refresh_token_repository import (
    SQLAlchemyRefreshTokenRepository,
)
from app.iam.infrastructure.repositories.teacher_repository import (
    SQLAlchemyTeacherRepository,
)
from app.iam.infrastructure.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from app.iam.presentation.mappers.request_mappers import RequestMapper
from app.iam.presentation.schemas import (
    RefreshRequest,
    RefreshResponse,
    SigninRequest,
    SigninResponse,
    SignoutRequest,
    SignoutResponse,
    SignupRequest,
    SignupResponse,
)

router = APIRouter(prefix="/iam", tags=["iam"])


def _build_services(
    db: Session,
) -> tuple[UserCommandServiceImpl, TeacherCommandServiceImpl]:
    user_repo: UserRepository = SQLAlchemyUserRepository(db)
    teacher_repo: TeacherRepository = SQLAlchemyTeacherRepository(db)
    refresh_repo: RefreshTokenRepository = SQLAlchemyRefreshTokenRepository(db)

    user_service = UserCommandServiceImpl(
        user_repo=user_repo,
        refresh_token_repo=refresh_repo,
    )
    teacher_service = TeacherCommandServiceImpl(
        user_service=user_service,
        teacher_repo=teacher_repo,
        user_repo=user_repo,
    )
    return user_service, teacher_service


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db),
) -> SignupResponse:
    context = RequestMapper.to_signup_context(request)
    _, teacher_service = _build_services(db)
    result = teacher_service.signup(context)
    db.commit()
    return SignupResponse(
        user_id=result.user_id,
        teacher_id=result.teacher_id,
        name=result.name,
        lastname=result.lastname,
        email=result.email,
        institute_name=result.institute_name,
        phone=result.phone,
        created_at=result.created_at,
    )


@router.post("/signin", response_model=SigninResponse)
def signin(
    request: SigninRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SigninResponse:
    context = RequestMapper.to_signin_context(request)
    user_service, _ = _build_services(db)
    access_token, refresh_token, expires_in = user_service.signin(context, settings)
    db.commit()
    result = AuthAssembler.to_signin_result(access_token, refresh_token, expires_in)
    return SigninResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    request: RefreshRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RefreshResponse:
    context = RequestMapper.to_refresh_context(request)
    user_service, _ = _build_services(db)
    access_token, refresh_token, expires_in = user_service.refresh(context, settings)
    db.commit()
    result = AuthAssembler.to_refresh_result(access_token, refresh_token, expires_in)
    return RefreshResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )


@router.post("/signout", response_model=SignoutResponse)
def signout(
    request: SignoutRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SignoutResponse:
    context = RequestMapper.to_signout_context(request)
    user_service, _ = _build_services(db)
    user_service.signout(context, settings)
    db.commit()
    result = AuthAssembler.to_signout_result()
    return SignoutResponse(message=result.message)
