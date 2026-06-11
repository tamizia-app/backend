from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.iam.infrastructure.models.user_model import UserModel
from app.profile.application.ports.repositories import TeacherRepository
from app.profile.application.ports.user_management_port import UserManagementPort
from app.profile.application.use_cases.get_teacher import GetTeacherUseCase
from app.profile.application.use_cases.update_teacher_profile import (
    UpdateTeacherCommand,
    UpdateTeacherProfileUseCase,
)
from app.profile.infrastructure.adapters.iam_adapter import IamAdapter
from app.profile.infrastructure.repositories.teacher_repository import (
    SQLAlchemyTeacherRepository,
)
from app.profile.presentation.schemas import TeacherResponse, UpdateTeacherRequest

router = APIRouter(prefix="/teachers", tags=["teachers"])


def _build_use_cases(
    db: Session,
) -> tuple[GetTeacherUseCase, UpdateTeacherProfileUseCase]:
    teacher_repo: TeacherRepository = SQLAlchemyTeacherRepository(db)
    user_mgmt: UserManagementPort = IamAdapter(db)
    get_use_case = GetTeacherUseCase(teacher_repo, user_mgmt)
    update_use_case = UpdateTeacherProfileUseCase(teacher_repo, user_mgmt)
    return get_use_case, update_use_case


@router.get("/me", response_model=TeacherResponse)
def get_my_teacher_profile(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> TeacherResponse:
    get_uc, _ = _build_use_cases(db)
    result = get_uc.execute(current_user.id)
    return TeacherResponse(
        teacher_id=result.teacher_id,
        name=result.name,
        lastname=result.lastname,
        email=result.email,
        institute_name=result.institute_name,
        phone=result.phone,
    )


@router.put("/me", response_model=TeacherResponse)
def update_my_teacher_profile(
    request: UpdateTeacherRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> TeacherResponse:
    _, update_uc = _build_use_cases(db)
    command = UpdateTeacherCommand(
        user_id=current_user.id,
        name=request.name,
        lastname=request.lastname,
        email=request.email,
        institute_name=request.institute_name,
        phone=request.phone,
    )
    result = update_uc.execute(command)
    db.commit()
    return TeacherResponse(
        teacher_id=result.teacher_id,
        name=result.name,
        lastname=result.lastname,
        email=result.email,
        institute_name=result.institute_name,
        phone=result.phone,
    )
