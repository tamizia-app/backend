from __future__ import annotations


class AIProcessingError(Exception):
    """Base exception for AI processing use cases."""


class WritingSampleRequiredError(AIProcessingError):
    pass


class AudioSampleRequiredError(AIProcessingError):
    pass


class SessionClosedForAnalysisError(AIProcessingError):
    pass


class EvidenceSourceNotFoundError(AIProcessingError):
    pass

