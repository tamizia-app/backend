from __future__ import annotations

from fastapi import HTTPException, UploadFile, status

from app.assessment.modules.evidences.domain.entities import EvidenceFile
from app.assessment.modules.evidences.domain.exceptions import EvidenceError, SessionClosedForEvidenceError


async def evidence_file_from_upload(upload_file: UploadFile, *, default_filename: str, default_content_type: str) -> EvidenceFile:
    return EvidenceFile(
        content=await upload_file.read(),
        filename=upload_file.filename or default_filename,
        content_type=upload_file.content_type or default_content_type,
    )


def raise_evidence_http_error(error: EvidenceError) -> None:
    if isinstance(error, SessionClosedForEvidenceError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is closed for new evidence.") from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evidence operation failed.") from error
