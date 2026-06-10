from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    name: str
    lastname: str
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
