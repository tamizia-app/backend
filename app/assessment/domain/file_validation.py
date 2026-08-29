from __future__ import annotations

import struct


def validate_image_content(content: bytes, content_type: str | None) -> tuple[bool, str | None]:
    if not content:
        return False, "EMPTY_IMAGE"
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized_type not in {"image/png", "image/jpeg", "image/jpg", "image/webp"}:
        return False, "UNSUPPORTED_IMAGE_TYPE"
    if normalized_type == "image/png":
        if len(content) < 33 or content[:8] != b"\x89PNG\r\n\x1a\n":
            return False, "INVALID_IMAGE_ENCODING"
        try:
            width, height = struct.unpack(">II", content[16:24])
        except struct.error:
            return False, "INVALID_IMAGE_ENCODING"
        if width <= 0 or height <= 0 or b"IEND" not in content:
            return False, "INVALID_IMAGE_ENCODING"
    elif normalized_type == "image/webp":
        if len(content) < 12 or content[:4] != b"RIFF" or content[8:12] != b"WEBP":
            return False, "INVALID_IMAGE_ENCODING"
    elif not (content.startswith(b"\xff\xd8") and content.endswith(b"\xff\xd9")):
        return False, "INVALID_IMAGE_ENCODING"
    return True, None
