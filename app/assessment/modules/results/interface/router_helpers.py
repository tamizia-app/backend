from __future__ import annotations

from fastapi import HTTPException, status

from app.assessment.modules.results.domain.exceptions import AnalysisRequiredError, ResultError, ResultNotFoundError


def raise_result_http_error(error: ResultError) -> None:
    if isinstance(error, AnalysisRequiredError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="At least one completed analysis is required.") from error
    if isinstance(error, ResultNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found.") from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Result operation failed.") from error
