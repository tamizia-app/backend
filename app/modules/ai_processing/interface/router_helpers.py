from __future__ import annotations

from fastapi import HTTPException, status

from app.modules.ai_processing.domain.exceptions import (
    AIProcessingError,
    AudioSampleRequiredError,
    SessionClosedForAnalysisError,
    WritingSampleRequiredError,
)


def raise_ai_processing_http_error(error: AIProcessingError) -> None:
    if isinstance(error, SessionClosedForAnalysisError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is closed for new evidence.") from error
    if isinstance(error, WritingSampleRequiredError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Writing sample is required before analysis.") from error
    if isinstance(error, AudioSampleRequiredError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Audio sample is required before analysis.") from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI processing operation failed.") from error

