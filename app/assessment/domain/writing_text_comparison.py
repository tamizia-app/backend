# =============================================================================
# [CAPTURA 3/3] CÁLCULO DE MÉTRICAS CER (Character Error Rate) Y WER (Word Error Rate)
# =============================================================================
# CER y WER miden qué tan diferente es el texto reconocido (por OCR o voz)
# respecto al texto esperado. Se usa Levenshtein distance para contar errores
# a nivel de caracteres (CER) y palabras (WER). Si son altos, se marca el
# ejercicio para revisión manual del docente.
# =============================================================================

from __future__ import annotations

import re
from dataclasses import dataclass, field

_PUNCTUATION_RE = re.compile(r"[.,;:!?¿¡\"'“”()\[\]]")


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = _PUNCTUATION_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def levenshtein_distance(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    if m < n:
        s1, s2 = s2, s1
        m, n = n, m
    prev = list(range(n + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[n]


def _word_levenshtein(expected_words: list[str], recognized_words: list[str]) -> int:
    m, n = len(expected_words), len(recognized_words)
    if m < n:
        expected_words, recognized_words = recognized_words, expected_words
        m, n = n, m
    prev = list(range(n + 1))
    for i, w1 in enumerate(expected_words):
        curr = [i + 1]
        for j, w2 in enumerate(recognized_words):
            cost = 0 if w1 == w2 else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[n]


def calculate_cer(expected: str, recognized: str) -> float:
    # CER = (distancia Levenshtein entre textos) / (largo del texto esperado)
    # Mide errores a nivel de cada caracter (letras, espacios)
    norm_exp = normalize_text(expected)
    norm_rec = normalize_text(recognized)
    if not norm_exp:
        return 1.0 if norm_rec else 0.0
    distance = levenshtein_distance(norm_exp, norm_rec)
    return round(distance / max(1, len(norm_exp)), 3)


def calculate_wer(expected: str, recognized: str) -> float:
    # WER = (distancia Levenshtein entre palabras) / (cantidad de palabras esperadas)
    # Mide errores a nivel de palabras completas
    norm_exp = normalize_text(expected)
    norm_rec = normalize_text(recognized)
    expected_words = norm_exp.split() if norm_exp else []
    recognized_words = norm_rec.split() if norm_rec else []
    if not expected_words:
        return 1.0 if recognized_words else 0.0
    distance = _word_levenshtein(expected_words, recognized_words)
    return round(distance / max(1, len(expected_words)), 3)


def calculate_similarity_score(cer: float, wer: float) -> float:
    char_score = max(0.0, 100.0 * (1.0 - cer))
    word_score = max(0.0, 100.0 * (1.0 - wer))
    return round(0.75 * char_score + 0.25 * word_score, 2)


def char_accuracy(cer: float) -> float:
    return round(max(0.0, 100.0 * (1.0 - cer)), 2)


def word_accuracy(wer: float) -> float:
    return round(max(0.0, 100.0 * (1.0 - wer)), 2)


@dataclass
class WritingReviewResult:
    cer: float
    wer: float
    similarity_score: float
    review_required: bool
    review_reasons: list[str] = field(default_factory=list)
    char_accuracy: float = 0.0
    word_accuracy: float = 0.0


def determine_writing_review(
    expected: str,
    recognized: str,
    confidence_avg: float | None = None,
) -> WritingReviewResult:
    # Si CER o WER superan umbrales, o la confianza del OCR es baja,
    # se marca el ejercicio para que el docente lo revise manualmente.
    if not recognized:
        return WritingReviewResult(
            cer=1.0,
            wer=1.0,
            similarity_score=0.0,
            review_required=True,
            review_reasons=["EMPTY_RECOGNIZED_TEXT"],
            char_accuracy=0.0,
            word_accuracy=0.0,
        )

    cer = calculate_cer(expected, recognized)
    wer = calculate_wer(expected, recognized)
    sim = calculate_similarity_score(cer, wer)
    c_acc = char_accuracy(cer)
    w_acc = word_accuracy(wer)

    reasons: list[str] = []
    if confidence_avg is not None and confidence_avg < 0.70:
        reasons.append("LOW_OCR_CONFIDENCE")
    if sim < 75:
        reasons.append("LOW_TEXT_SIMILARITY")
    if cer >= 0.25:
        reasons.append("HIGH_CHARACTER_ERROR_RATE")
    if wer >= 0.50 and c_acc < 85:
        reasons.append("HIGH_WORD_ERROR_RATE")

    review_required = len(reasons) > 0

    return WritingReviewResult(
        cer=cer,
        wer=wer,
        similarity_score=sim,
        review_required=review_required,
        review_reasons=reasons,
        char_accuracy=c_acc,
        word_accuracy=w_acc,
    )
