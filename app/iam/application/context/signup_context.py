from dataclasses import dataclass


@dataclass
class SignupContext:
    name: str
    lastname: str
    email: str
    password: str
