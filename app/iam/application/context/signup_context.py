from dataclasses import dataclass


@dataclass
class SignupContext:
    name: str
    lastname: str
    email: str
    password: str
    institute_name: str | None
    phone: str | None
