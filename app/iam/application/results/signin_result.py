from dataclasses import dataclass


@dataclass
class SigninResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
