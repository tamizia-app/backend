from dataclasses import dataclass


@dataclass
class SignoutContext:
    refresh_token: str
