"""Deterministic fit checks used as the source of truth for AI retries."""

from dataclasses import dataclass
from typing import Optional

from counters import char_count, word_count


@dataclass
class FitConstraints:
    min_words: Optional[int] = None
    max_words: Optional[int] = None
    min_chars: Optional[int] = None
    max_chars: Optional[int] = None


@dataclass
class FitCheck:
    word_count: int
    char_count: int
    met_target: bool
    misses: list[str]


def check_fit(text: str, constraints: FitConstraints) -> FitCheck:
    words = word_count(text)
    chars = char_count(text)
    misses = []

    if constraints.min_words is not None and words < constraints.min_words:
        misses.append(f"{constraints.min_words - words} words under the {constraints.min_words} minimum")
    if constraints.max_words is not None and words > constraints.max_words:
        misses.append(f"{words - constraints.max_words} words over the {constraints.max_words} maximum")
    if constraints.min_chars is not None and chars < constraints.min_chars:
        misses.append(f"{constraints.min_chars - chars} characters under the {constraints.min_chars} minimum")
    if constraints.max_chars is not None and chars > constraints.max_chars:
        misses.append(f"{chars - constraints.max_chars} characters over the {constraints.max_chars} maximum")

    return FitCheck(
        word_count=words,
        char_count=chars,
        met_target=not misses,
        misses=misses,
    )
