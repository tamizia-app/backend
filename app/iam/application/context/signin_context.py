from dataclasses import dataclass


@dataclass
class SigninContext:
    email: str
    password: str
