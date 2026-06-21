from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class CreatePasswordResetTokenCommand:
    user_id: UUID
    token_hash: str
    expires_at: datetime
