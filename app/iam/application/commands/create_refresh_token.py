from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateRefreshTokenCommand:
    user_id: UUID
    token_hash: str
