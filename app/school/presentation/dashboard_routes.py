from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.iam.infrastructure.models.user_model import UserModel
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
from app.school.infrastructure.models.classroom_model import ClassroomModel
from app.school.infrastructure.models.student_model import Student
from app.assessment.infrastructure.models.attempt_model import AssessmentAttemptModel
from app.assessment.infrastructure.models.template_model import AssessmentTemplateModel
from app.assessment.infrastructure.models.assessment_model import AssessmentModel

dashboard_router = APIRouter(tags=["dashboard"])


class DashboardSummaryResponse(BaseModel):
    total_students: int = 0
    total_classrooms: int = 0
    total_templates: int = 0
    total_assessments: int = 0
    completed_attempts: int = 0
    in_progress_attempts: int = 0


@dashboard_router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> DashboardSummaryResponse:
    teacher = db.query(HomeroomTeacherModel).filter(HomeroomTeacherModel.user_id == current_user.id).first()
    if not teacher:
        return DashboardSummaryResponse()

    teacher_id = teacher.id

    classroom_ids = db.scalars(
        select(ClassroomModel.id).where(ClassroomModel.homeroom_teacher_id == teacher_id)
    ).all()

    total_classrooms = len(classroom_ids)
    total_students = 0
    if classroom_ids:
        total_students = db.scalar(
            select(func.count(Student.id)).where(
                Student.classroom_id.in_(classroom_ids),
                Student.is_active == True,
            )
        ) or 0

    total_templates = db.scalar(
        select(func.count(AssessmentTemplateModel.id)).where(
            AssessmentTemplateModel.created_by_teacher_id == teacher_id
        )
    ) or 0

    total_assessments = db.scalar(
        select(func.count(AssessmentModel.id)).where(
            AssessmentModel.homeroom_teacher_id == teacher_id
        )
    ) or 0

    completed_attempts = db.scalar(
        select(func.count(AssessmentAttemptModel.id)).where(
            AssessmentAttemptModel.status == "COMPLETED",
            AssessmentAttemptModel.assessment_id.in_(
                select(AssessmentModel.id).where(AssessmentModel.homeroom_teacher_id == teacher_id)
            ),
        )
    ) or 0

    in_progress_attempts = db.scalar(
        select(func.count(AssessmentAttemptModel.id)).where(
            AssessmentAttemptModel.status == "IN_PROGRESS",
            AssessmentAttemptModel.assessment_id.in_(
                select(AssessmentModel.id).where(AssessmentModel.homeroom_teacher_id == teacher_id)
            ),
        )
    ) or 0

    return DashboardSummaryResponse(
        total_students=total_students,
        total_classrooms=total_classrooms,
        total_templates=total_templates,
        total_assessments=total_assessments,
        completed_attempts=completed_attempts,
        in_progress_attempts=in_progress_attempts,
    )
