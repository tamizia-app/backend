from dataclasses import dataclass


@dataclass
class SignupResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
