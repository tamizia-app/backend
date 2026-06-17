from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.iam.infrastructure.models.user_model import UserModel
from app.school.application.ports.repositories import HomeroomTeacherRepository
from app.school.application.ports.user_management_port import UserManagementPort
from app.school.application.use_cases.get_homeroom_teacher import (
    GetHomeroomTeacherUseCase,
)
from app.school.application.use_cases.update_homeroom_teacher import (
    UpdateHomeroomTeacherCommand,
    UpdateHomeroomTeacherUseCase,
)
from app.school.infrastructure.adapters.iam_adapter import IamAdapter
from app.school.infrastructure.repositories.homeroom_teacher_repository import (
    SQLAlchemyHomeroomTeacherRepository,
)
from app.school.presentation.schemas import (
    HomeroomTeacherResponse,
    UpdateHomeroomTeacherRequest,
)

teacher_router = APIRouter(tags=["teachers"])


def _build_teacher_use_cases(
    db: Session,
) -> tuple[GetHomeroomTeacherUseCase, UpdateHomeroomTeacherUseCase]:
    teacher_repo: HomeroomTeacherRepository = SQLAlchemyHomeroomTeacherRepository(db)
    user_mgmt: UserManagementPort = IamAdapter(db)
    get_use_case = GetHomeroomTeacherUseCase(teacher_repo, user_mgmt)
    update_use_case = UpdateHomeroomTeacherUseCase(teacher_repo, user_mgmt)
    return get_use_case, update_use_case


@teacher_router.get("/teachers/me", response_model=HomeroomTeacherResponse)
def get_my_teacher_profile(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> HomeroomTeacherResponse:
    get_uc, _ = _build_teacher_use_cases(db)
    result = get_uc.execute(current_user.id)
    return HomeroomTeacherResponse(
        teacher_id=result.teacher_id,
        name=result.name,
        lastname=result.lastname,
        email=result.email,
        institute_name=result.institute_name,
        phone=result.phone,
    )


@teacher_router.put("/teachers/me", response_model=HomeroomTeacherResponse)
def update_my_teacher_profile(
    request: UpdateHomeroomTeacherRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> HomeroomTeacherResponse:
    _, update_uc = _build_teacher_use_cases(db)
    command = UpdateHomeroomTeacherCommand(
        user_id=current_user.id,
        name=request.name,
        lastname=request.lastname,
        email=request.email,
        institute_name=request.institute_name,
        phone=request.phone,
    )
    result = update_uc.execute(command)
    db.commit()
    return HomeroomTeacherResponse(
        teacher_id=result.teacher_id,
        name=result.name,
        lastname=result.lastname,
        email=result.email,
        institute_name=result.institute_name,
        phone=result.phone,
    )
