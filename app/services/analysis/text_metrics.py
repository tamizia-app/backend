from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def levenshtein_distance(source: str, target: str) -> int:
    if source == target:
        return 0
    if not source:
        return len(target)
    if not target:
        return len(source)

    previous = list(range(len(target) + 1))
    for i, source_char in enumerate(source, start=1):
        current = [i]
        for j, target_char in enumerate(target, start=1):
            insertions = previous[j] + 1
            deletions = current[j - 1] + 1
            substitutions = previous[j - 1] + (source_char != target_char)
            current.append(min(insertions, deletions, substitutions))
        previous = current
    return previous[-1]


def cer(reference_text: str, observed_text: str) -> float:
    reference = normalize_text(reference_text)
    observed = normalize_text(observed_text)
    if not reference:
        return 0.0
    return levenshtein_distance(reference, observed) / max(len(reference), 1)


def wer(reference_text: str, observed_text: str) -> float:
    reference_words = normalize_text(reference_text).split()
    observed_words = normalize_text(observed_text).split()
    if not reference_words:
        return 0.0

    previous = list(range(len(observed_words) + 1))
    for i, ref_word in enumerate(reference_words, start=1):
        current = [i]
        for j, obs_word in enumerate(observed_words, start=1):
            insertions = previous[j] + 1
            deletions = current[j - 1] + 1
            substitutions = previous[j - 1] + (ref_word != obs_word)
            current.append(min(insertions, deletions, substitutions))
        previous = current
    return previous[-1] / max(len(reference_words), 1)


def omission_and_substitution_counts(reference_text: str, observed_text: str) -> tuple[int, int]:
    reference_words = normalize_text(reference_text).split()
    observed_words = normalize_text(observed_text).split()

    omissions = max(0, len(reference_words) - len(observed_words))
    substitutions = sum(
        1
        for ref_word, obs_word in zip(reference_words, observed_words, strict=False)
        if ref_word != obs_word
    )
    return omissions, substitutions


def build_writing_score(
    *,
    cer_score: float | None,
    wer_score: float | None,
    omissions: int | None,
    substitutions: int | None,
) -> float | None:
    if cer_score is None and wer_score is None:
        return None

    cer_component = (cer_score or 0.0) * 45
    wer_component = (wer_score or 0.0) * 45
    omission_penalty = (omissions or 0) * 3
    substitution_penalty = (substitutions or 0) * 2
    score = max(0.0, 100.0 - cer_component - wer_component - omission_penalty - substitution_penalty)
    return round(score, 2)


def build_reading_score(
    *,
    accuracy_score: float | None,
    fluency_score: float | None,
    completeness_score: float | None,
    pronunciation_score: float | None,
) -> float | None:
    values = [value for value in [accuracy_score, fluency_score, completeness_score, pronunciation_score] if value is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)

