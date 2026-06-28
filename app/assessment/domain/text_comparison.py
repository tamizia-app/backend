from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TextToken:
    original: str
    normalized: str


@dataclass(frozen=True)
class AlignmentItem:
    expected: str | None
    recognized: str | None
    expected_normalized: str | None
    recognized_normalized: str | None
    operation: str


@dataclass(frozen=True)
class WordComparison:
    expected_text: str
    recognized_text: str
    expected_normalized_text: str
    recognized_normalized_text: str
    expected_word_count: int
    recognized_word_count: int
    matches: int
    substitutions: int
    omissions: int
    insertions: int
    lexical_match_percentage: float
    wer: float | None
    wer_percentage: float | None
    alignment: list[AlignmentItem]

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "alignment": [asdict(item) for item in self.alignment],
        }


def tokenize(text: str) -> list[TextToken]:
    """Tokenize Unicode text while retaining accents and presentation forms."""
    normalized_unicode = unicodedata.normalize("NFC", text or "")
    cleaned = "".join(
        " " if unicodedata.category(char)[0] in {"P", "Z"} else char
        for char in normalized_unicode
    )
    originals = cleaned.split()
    return [
        TextToken(original=word, normalized=unicodedata.normalize("NFC", word).casefold())
        for word in originals
    ]


def compare_texts(expected_text: str, recognized_text: str) -> WordComparison:
    expected = tokenize(expected_text)
    recognized = tokenize(recognized_text)
    rows, columns = len(expected) + 1, len(recognized) + 1
    costs = [[0] * columns for _ in range(rows)]
    operations = [[""] * columns for _ in range(rows)]

    for i in range(1, rows):
        costs[i][0] = i
        operations[i][0] = "omission"
    for j in range(1, columns):
        costs[0][j] = j
        operations[0][j] = "insertion"

    # Stable precedence makes repeated-word alignments deterministic.
    precedence = {"match": 0, "substitution": 1, "omission": 2, "insertion": 3}
    for i in range(1, rows):
        for j in range(1, columns):
            same = expected[i - 1].normalized == recognized[j - 1].normalized
            diagonal_operation = "match" if same else "substitution"
            candidates = [
                (costs[i - 1][j - 1] + (0 if same else 1), diagonal_operation),
                (costs[i - 1][j] + 1, "omission"),
                (costs[i][j - 1] + 1, "insertion"),
            ]
            costs[i][j], operations[i][j] = min(
                candidates, key=lambda item: (item[0], precedence[item[1]])
            )

    alignment: list[AlignmentItem] = []
    i, j = len(expected), len(recognized)
    while i or j:
        operation = operations[i][j]
        if operation in {"match", "substitution"}:
            expected_token, recognized_token = expected[i - 1], recognized[j - 1]
            alignment.append(
                AlignmentItem(
                    expected=expected_token.original,
                    recognized=recognized_token.original,
                    expected_normalized=expected_token.normalized,
                    recognized_normalized=recognized_token.normalized,
                    operation=operation,
                )
            )
            i -= 1
            j -= 1
        elif operation == "omission":
            token = expected[i - 1]
            alignment.append(
                AlignmentItem(
                    expected=token.original,
                    recognized=None,
                    expected_normalized=token.normalized,
                    recognized_normalized=None,
                    operation=operation,
                )
            )
            i -= 1
        else:
            token = recognized[j - 1]
            alignment.append(
                AlignmentItem(
                    expected=None,
                    recognized=token.original,
                    expected_normalized=None,
                    recognized_normalized=token.normalized,
                    operation="insertion",
                )
            )
            j -= 1

    alignment.reverse()
    counts = {
        operation: sum(item.operation == operation for item in alignment)
        for operation in ("match", "substitution", "omission", "insertion")
    }
    expected_count = len(expected)
    errors = counts["substitution"] + counts["omission"] + counts["insertion"]
    wer = errors / expected_count if expected_count else None
    lexical_match = counts["match"] / expected_count * 100 if expected_count else 0.0

    return WordComparison(
        expected_text=expected_text,
        recognized_text=recognized_text,
        expected_normalized_text=" ".join(token.normalized for token in expected),
        recognized_normalized_text=" ".join(token.normalized for token in recognized),
        expected_word_count=expected_count,
        recognized_word_count=len(recognized),
        matches=counts["match"],
        substitutions=counts["substitution"],
        omissions=counts["omission"],
        insertions=counts["insertion"],
        lexical_match_percentage=round(lexical_match, 2),
        wer=round(wer, 4) if wer is not None else None,
        wer_percentage=round(wer * 100, 2) if wer is not None else None,
        alignment=alignment,
    )
