from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.iam.infrastructure.models.user_model import UserModel
from app.school.application.use_cases.create_student import CreateStudentCommand, CreateStudentUseCase
from app.school.application.use_cases.delete_student import DeleteStudentCommand, DeleteStudentUseCase
from app.school.application.use_cases.download_consent import DownloadConsentQuery, DownloadConsentUseCase
from app.school.application.use_cases.get_student import GetStudentQuery, GetStudentUseCase
from app.school.application.use_cases.list_students import ListStudentsQuery, ListStudentsUseCase
from app.school.application.use_cases.revoke_consent import RevokeConsentCommand, RevokeConsentUseCase
from app.school.application.use_cases.update_student import UpdateStudentCommand, UpdateStudentUseCase
from app.school.application.use_cases.upload_consent import UploadConsentCommand, UploadConsentUseCase
from app.school.infrastructure.adapters.blob_storage import AzureConsentBlobStorage
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
from app.school.infrastructure.repositories.student_repository import (
    SQLAlchemyStudentConsentRepository,
    SQLAlchemyStudentRepository,
)
from app.school.presentation.schemas import (
    CreateStudentRequest,
    StudentConsentResponse,
    StudentResponse,
    UpdateStudentRequest,
)

student_router = APIRouter(tags=["students"])


def _student_repo(db: Session) -> SQLAlchemyStudentRepository:
    return SQLAlchemyStudentRepository(db)


def _consent_repo(db: Session) -> SQLAlchemyStudentConsentRepository:
    return SQLAlchemyStudentConsentRepository(db)


def _blob_storage() -> AzureConsentBlobStorage:
    return AzureConsentBlobStorage(get_settings())


def _resolve_teacher_id(db: Session, user_id: str) -> UUID:
    teacher = db.query(HomeroomTeacherModel).filter(HomeroomTeacherModel.user_id == user_id).first()
    if not teacher:
        raise HTTPException(status_code=400, detail="Teacher profile not found")
    return teacher.id


MAX_CONSENT_FILE_SIZE = 10 * 1024 * 1024


@student_router.post("/classrooms/{classroom_id}/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    classroom_id: UUID,
    request: CreateStudentRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentResponse:
    _resolve_teacher_id(db, current_user.id)
    uc = CreateStudentUseCase(_student_repo(db))
    result = uc.execute(
        CreateStudentCommand(
            classroom_id=classroom_id,
            code=request.code,
            age=request.age,
            gender=request.gender,
        )
    )
    db.commit()
    return StudentResponse(
        student_id=result.student_id,
        classroom_id=result.classroom_id,
        code=result.code,
        age=result.age,
        gender=result.gender,
        is_active=result.is_active,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@student_router.get("/classrooms/{classroom_id}/students", response_model=list[StudentResponse])
def list_students(
    classroom_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[StudentResponse]:
    _resolve_teacher_id(db, current_user.id)
    uc = ListStudentsUseCase(_student_repo(db))
    results = uc.execute(ListStudentsQuery(classroom_id=classroom_id))
    return [
        StudentResponse(
            student_id=r.student_id,
            classroom_id=r.classroom_id,
            code=r.code,
            age=r.age,
            gender=r.gender,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in results
    ]


@student_router.get("/students/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentResponse:
    _resolve_teacher_id(db, current_user.id)
    uc = GetStudentUseCase(_student_repo(db))
    result = uc.execute(GetStudentQuery(student_id=student_id))
    return StudentResponse(
        student_id=result.student_id,
        classroom_id=result.classroom_id,
        code=result.code,
        age=result.age,
        gender=result.gender,
        is_active=result.is_active,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@student_router.put("/students/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: UUID,
    request: UpdateStudentRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)
    uc = UpdateStudentUseCase(_student_repo(db))
    result = uc.execute(
        UpdateStudentCommand(
            student_id=student_id,
            code=request.code,
            age=request.age,
            gender=request.gender,
        )
    )
    db.commit()
    return StudentResponse(
        student_id=result.student_id,
        classroom_id=result.classroom_id,
        code=result.code,
        age=result.age,
        gender=result.gender,
        is_active=result.is_active,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@student_router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    _resolve_teacher_id(db, current_user.id)
    uc = DeleteStudentUseCase(_student_repo(db))
    uc.execute(DeleteStudentCommand(student_id=student_id))
    db.commit()


@student_router.post("/students/{student_id}/consent/upload", response_model=StudentConsentResponse)
def upload_consent(
    student_id: UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentConsentResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    content = file.file.read()
    if len(content) > MAX_CONSENT_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 10 MB limit")

    student = _student_repo(db).find_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    uc = UploadConsentUseCase(_student_repo(db), _consent_repo(db), _blob_storage())
    result = uc.execute(
        UploadConsentCommand(
            student_id=student_id,
            teacher_id=teacher_id,
            classroom_id=student.classroom_id,
            content=content,
        )
    )
    db.commit()
    return StudentConsentResponse(
        consent_id=result.consent_id,
        student_id=result.student_id,
        status=result.status,
        consent_date=result.consent_date,
        revoked_at=result.revoked_at,
        evidence_blob_path=result.evidence_blob_path,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@student_router.post("/students/{student_id}/consent/revoke", response_model=StudentConsentResponse)
def revoke_consent(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentConsentResponse:
    teacher_id = _resolve_teacher_id(db, current_user.id)

    student = _student_repo(db).find_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    uc = RevokeConsentUseCase(_student_repo(db), _consent_repo(db), _blob_storage())
    result = uc.execute(
        RevokeConsentCommand(
            student_id=student_id,
            teacher_id=teacher_id,
            classroom_id=student.classroom_id,
        )
    )
    db.commit()
    return StudentConsentResponse(
        consent_id=result.consent_id,
        student_id=result.student_id,
        status=result.status,
        consent_date=result.consent_date,
        revoked_at=result.revoked_at,
        evidence_blob_path=result.evidence_blob_path,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@student_router.get("/students/consent/template")
def download_consent_template(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    _resolve_teacher_id(db, current_user.id)
    url = _blob_storage().template_url()
    return {"download_url": url}


@student_router.get("/students/{student_id}/consent", response_model=StudentConsentResponse)
def get_consent_status(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StudentConsentResponse:
    _resolve_teacher_id(db, current_user.id)
    result = _consent_repo(db).find_by_student_id(student_id)
    if not result:
        raise HTTPException(status_code=404, detail="Consent not found")
    return StudentConsentResponse(
        consent_id=result.id,
        student_id=result.student_id,
        status=result.status,
        consent_date=result.consent_date,
        revoked_at=result.revoked_at,
        evidence_blob_path=result.evidence_blob_path,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@student_router.get("/students/{student_id}/consent/download")
def download_consent(
    student_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    from io import BytesIO
    from fastapi.responses import StreamingResponse

    _resolve_teacher_id(db, current_user.id)
    storage = _blob_storage()
    consent = _consent_repo(db).find_by_student_id(student_id)
    if not consent or not consent.evidence_blob_path:
        raise HTTPException(status_code=404, detail="Consent not found")

    content = storage.get_pdf_content(blob_path=consent.evidence_blob_path)
    if content is not None:
        return StreamingResponse(BytesIO(content), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=consentimiento.pdf"})

    url = storage.download_url(blob_path=consent.evidence_blob_path)
    return {"download_url": url}
