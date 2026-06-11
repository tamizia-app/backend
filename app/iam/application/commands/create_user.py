from dataclasses import dataclass


@dataclass
class CreateUserCommand:
    name: str
    lastname: str
    email: str
    password_hash: str
