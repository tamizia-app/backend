from dataclasses import dataclass
from uuid import UUID


@dataclass
class SignupCommand:
    user_id: UUID
    institute_name: str | None
    phone: str | None
