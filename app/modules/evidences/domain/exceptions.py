from __future__ import annotations


class EvidenceError(Exception):
    """Base exception for evidence use cases."""


class SessionClosedForEvidenceError(EvidenceError):
    pass


class EvidenceStorageError(EvidenceError):
    pass

