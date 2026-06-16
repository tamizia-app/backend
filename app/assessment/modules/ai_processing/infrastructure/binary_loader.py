from __future__ import annotations

from pathlib import Path

import httpx


class HTTPOrLocalBinarySourceLoader:
    def load(self, location: str) -> bytes:
        if location.startswith("http://") or location.startswith("https://"):
            response = httpx.get(location, timeout=60.0)
            response.raise_for_status()
            return response.content
        return Path(location).read_bytes()

