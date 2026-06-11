from dataclasses import dataclass


@dataclass
class RefreshContext:
    refresh_token: str
