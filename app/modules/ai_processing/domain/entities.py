from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextComparison:
    cer_score: float
    wer_score: float
    omissions: int
    substitutions: int


@dataclass(frozen=True)
class WritingMetrics:
    comparison: TextComparison
    writing_score: float | None


@dataclass(frozen=True)
class ReadingMetrics:
    reading_score: float | None

