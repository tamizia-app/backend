from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class RefreshToken:
    id: UUID
    user_id: UUID
    token_hash: str
    created_at: datetime
    revoked_at: datetime | None
