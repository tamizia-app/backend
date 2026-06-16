import sys
sys.path.insert(0, ".")

# IAM
from app.iam.domain.user import User
from app.iam.domain.refresh_token import RefreshToken
from app.iam.application.services.user_command_service import UserCommandServiceImpl
from app.iam.presentation.routes import router as iam_router
from app.iam.facade.user_facade import IamUserFacade

# School - HomeroomTeacher
from app.school.domain.homeroom_teacher import HomeroomTeacher
from app.school.application.use_cases.get_homeroom_teacher import GetHomeroomTeacherUseCase
from app.school.application.use_cases.update_homeroom_teacher import UpdateHomeroomTeacherUseCase, UpdateHomeroomTeacherCommand
from app.school.application.ports.repositories import HomeroomTeacherRepository
from app.school.application.ports.user_management_port import UserManagementPort, UserData
from app.school.infrastructure.repositories.homeroom_teacher_repository import SQLAlchemyHomeroomTeacherRepository
from app.school.infrastructure.adapters.iam_adapter import IamAdapter
from app.school.infrastructure.models.homeroom_teacher_model import HomeroomTeacherModel
from app.school.presentation.routes import router as school_router

# App
from app.main import app

print("All imports OK after refactor")
print(f"App routes: {len(app.routes)}")
