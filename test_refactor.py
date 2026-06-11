import sys
sys.path.insert(0, ".")

# IAM - only User, RefreshToken, auth
from app.iam.domain.user import User
from app.iam.domain.refresh_token import RefreshToken
from app.iam.application.services.user_command_service import UserCommandServiceImpl
from app.iam.presentation.routes import router as iam_router
from app.iam.facade.user_facade import IamUserFacade

# Profile - Teacher
from app.profile.domain.teacher import Teacher
from app.profile.application.use_cases.get_teacher import GetTeacherUseCase
from app.profile.application.use_cases.update_teacher_profile import UpdateTeacherProfileUseCase
from app.profile.application.ports.repositories import TeacherRepository
from app.profile.application.ports.user_management_port import UserManagementPort, UserData
from app.profile.infrastructure.repositories.teacher_repository import SQLAlchemyTeacherRepository
from app.profile.infrastructure.adapters.iam_adapter import IamAdapter
from app.profile.infrastructure.models.teacher_model import TeacherModel
from app.profile.presentation.routes import router as profile_router

# App
from app.main import app

print("All imports OK after refactor")
print(f"App routes: {len(app.routes)}")
