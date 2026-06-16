from uuid import UUID

from app.iam.application.ports.repositories import UserRepository
from app.school.application.ports.user_management_port import (
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
        self._user_repo.update(user_id, name, lastname, email)
