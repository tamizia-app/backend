from dataclasses import dataclass
from uuid import UUID


@dataclass
class UserData:
    user_id: UUID
    name: str
    lastname: str
    email: str


class UserManagementPort:
    def get_user(self, user_id: UUID) -> UserData | None:
        raise NotImplementedError

    def update_user(self, user_id: UUID, name: str, lastname: str, email: str) -> None:
        raise NotImplementedError
