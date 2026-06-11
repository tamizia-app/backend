from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.iam.application.assemblers.auth_assembler import AuthAssembler
from app.iam.application.ports.repositories import (
    RefreshTokenRepository,
    UserRepository,
)
from app.iam.application.services.user_command_service import (
    UserCommandServiceImpl,
)
from app.iam.infrastructure.repositories.refresh_token_repository import (
    SQLAlchemyRefreshTokenRepository,
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
    SigninResponse as SignupResponse,
)
from app.profile.application.use_cases.create_teacher import (
    CreateTeacherCommand,
    CreateTeacherUseCase,
)
from app.profile.infrastructure.adapters.iam_adapter import IamAdapter
from app.profile.infrastructure.repositories.teacher_repository import (
    SQLAlchemyTeacherRepository,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_service(db: Session) -> UserCommandServiceImpl:
    user_repo: UserRepository = SQLAlchemyUserRepository(db)
    refresh_repo: RefreshTokenRepository = SQLAlchemyRefreshTokenRepository(db)
    return UserCommandServiceImpl(user_repo=user_repo, refresh_token_repo=refresh_repo)


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SignupResponse:
    context = RequestMapper.to_signup_context(request)
    service = _build_service(db)
    access_token, refresh_token, expires_in = service.signup(context, settings)

    user_repo: UserRepository = SQLAlchemyUserRepository(db)
    user = user_repo.find_by_email(context.email)
    if user:
        create_teacher = CreateTeacherUseCase(
            teacher_repo=SQLAlchemyTeacherRepository(db),
            user_management=IamAdapter(db),
        )
        create_teacher.execute(
            CreateTeacherCommand(
                user_id=user.id,
                institute_name=request.institute_name,
                phone=request.phone,
            )
        )

    db.commit()
    result = AuthAssembler.to_signup_result(access_token, refresh_token, expires_in)
    return SignupResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )


@router.post("/signin", response_model=SigninResponse)
def signin(
    request: SigninRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SigninResponse:
    context = RequestMapper.to_signin_context(request)
    service = _build_service(db)
    access_token, refresh_token, expires_in = service.signin(context, settings)
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
    service = _build_service(db)
    access_token, refresh_token, expires_in = service.refresh(context, settings)
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
    service = _build_service(db)
    service.signout(context, settings)
    db.commit()
    result = AuthAssembler.to_signout_result()
    return SignoutResponse(message=result.message)
