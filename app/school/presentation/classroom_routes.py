from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from fastapi import HTTPException

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.iam.infrastructure.models.user_model import UserModel
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
from app.school.application.use_cases.create_classroom import (
    CreateClassroomCommand,
    CreateClassroomUseCase,
)
from app.school.application.use_cases.delete_classroom import (
    DeleteClassroomCommand,
    DeleteClassroomUseCase,
)
from app.school.application.use_cases.get_classroom import (
    GetClassroomQuery,
    GetClassroomUseCase,
)
from app.school.application.use_cases.list_classrooms_by_teacher import (
    ListClassroomsByTeacherQuery,
    ListClassroomsByTeacherUseCase,
)
from app.school.application.use_cases.update_classroom import (
    UpdateClassroomCommand,
    UpdateClassroomUseCase,
)
from app.school.infrastructure.repositories.classroom_repository import (
    SQLAlchemyClassroomRepository,
)
from app.school.presentation.schemas import (
    ClassroomResponse,
    CreateClassroomRequest,
    UpdateClassroomRequest,
)

classroom_router = APIRouter(tags=["classrooms"])


def _classroom_repo(db: Session) -> SQLAlchemyClassroomRepository:
    return SQLAlchemyClassroomRepository(db)


def _resolve_teacher_id(db: Session, user_id: str) -> str:
    teacher = db.query(HomeroomTeacherModel).filter(HomeroomTeacherModel.user_id == user_id).first()
    if not teacher:
        raise HTTPException(status_code=400, detail="Teacher profile not found")
    return teacher.id


@classroom_router.post("/classrooms", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
def create_classroom(
    request: CreateClassroomRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ClassroomResponse:
    homeroom_teacher_id = _resolve_teacher_id(db, current_user.id)
    uc = CreateClassroomUseCase(_classroom_repo(db))
    result = uc.execute(
        CreateClassroomCommand(
            homeroom_teacher_id=homeroom_teacher_id,
            name=request.name,
            grade_level=request.grade_level,
            section=request.section,
            school_year=request.school_year,
        )
    )
    db.commit()
    return ClassroomResponse(
        classroom_id=result.classroom_id,
        homeroom_teacher_id=result.homeroom_teacher_id,
        name=result.name,
        grade_level=result.grade_level,
        section=result.section,
        school_year=result.school_year,
    )


@classroom_router.get("/classrooms", response_model=list[ClassroomResponse])
def list_classrooms(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[ClassroomResponse]:
    homeroom_teacher_id = _resolve_teacher_id(db, current_user.id)
    uc = ListClassroomsByTeacherUseCase(_classroom_repo(db))
    results = uc.execute(ListClassroomsByTeacherQuery(homeroom_teacher_id=homeroom_teacher_id))
    return [
        ClassroomResponse(
            classroom_id=r.classroom_id,
            homeroom_teacher_id=r.homeroom_teacher_id,
            name=r.name,
            grade_level=r.grade_level,
            section=r.section,
            school_year=r.school_year,
        )
        for r in results
    ]


@classroom_router.get("/classrooms/{classroom_id}", response_model=ClassroomResponse)
def get_classroom(
    classroom_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ClassroomResponse:
    uc = GetClassroomUseCase(_classroom_repo(db))
    result = uc.execute(GetClassroomQuery(classroom_id=classroom_id))
    return ClassroomResponse(
        classroom_id=result.classroom_id,
        homeroom_teacher_id=result.homeroom_teacher_id,
        name=result.name,
        grade_level=result.grade_level,
        section=result.section,
        school_year=result.school_year,
    )


@classroom_router.put("/classrooms/{classroom_id}", response_model=ClassroomResponse)
def update_classroom(
    classroom_id: UUID,
    request: UpdateClassroomRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ClassroomResponse:
    homeroom_teacher_id = _resolve_teacher_id(db, current_user.id)
    uc = UpdateClassroomUseCase(_classroom_repo(db))
    result = uc.execute(
        UpdateClassroomCommand(
            classroom_id=classroom_id,
            homeroom_teacher_id=homeroom_teacher_id,
            name=request.name,
            grade_level=request.grade_level,
            section=request.section,
            school_year=request.school_year,
        )
    )
    db.commit()
    return ClassroomResponse(
        classroom_id=result.classroom_id,
        homeroom_teacher_id=result.homeroom_teacher_id,
        name=result.name,
        grade_level=result.grade_level,
        section=result.section,
        school_year=result.school_year,
    )


@classroom_router.delete("/classrooms/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(
    classroom_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    uc = DeleteClassroomUseCase(_classroom_repo(db))
    uc.execute(DeleteClassroomCommand(classroom_id=classroom_id))
    db.commit()
