from dataclasses import dataclass


@dataclass
class ResetPasswordContext:
    token: str
    new_password: str
