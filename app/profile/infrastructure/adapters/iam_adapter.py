from uuid import UUID

from app.iam.facade.user_facade import IamUserFacade
from app.iam.infrastructure.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from app.profile.application.ports.user_management_port import (
    UserData,
    UserManagementPort,
)
from sqlalchemy.orm import Session


class IamAdapter(UserManagementPort):
    def __init__(self, db: Session) -> None:
        self._facade = IamUserFacade(SQLAlchemyUserRepository(db))

    def get_user(self, user_id: UUID) -> UserData | None:
        return self._facade.get_user(user_id)

    def update_user(self, user_id: UUID, name: str, lastname: str, email: str) -> None:
        self._facade.update_user(user_id, name, lastname, email)
