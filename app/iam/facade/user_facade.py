from uuid import UUID

from app.iam.application.ports.repositories import UserRepository
from app.profile.application.ports.user_management_port import (
    UserData,
    UserManagementPort,
)


class IamUserFacade(UserManagementPort):
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    def get_user(self, user_id: UUID) -> UserData | None:
        user = self._user_repo.find_by_id(user_id)
        if not user:
            return None
        return UserData(
            user_id=user.id,
            name=user.name,
            lastname=user.lastname,
            email=user.email,
        )

    def update_user(self, user_id: UUID, name: str, lastname: str, email: str) -> None:
        user = self._user_repo.find_by_id(user_id)
        if user:
            from app.iam.infrastructure.models.user_model import UserModel
            from app.db.session import SessionLocal

            db = SessionLocal()
            try:
                model = db.get(UserModel, user_id)
                if model:
                    model.name = name
                    model.lastname = lastname
                    model.email = email
                    db.commit()
            finally:
                db.close()
