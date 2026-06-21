from dataclasses import dataclass


@dataclass
class ForgotPasswordContext:
    email: str
