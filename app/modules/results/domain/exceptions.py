from __future__ import annotations


class ResultError(Exception):
    """Base exception for result use cases."""


class ResultNotFoundError(ResultError):
    pass


class AnalysisRequiredError(ResultError):
    pass

