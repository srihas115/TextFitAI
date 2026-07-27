"""Counting helpers used as the backend source of truth."""


def word_count(text: str) -> int:
    return len(text.split())


def char_count(text: str) -> int:
    return len(text)


def counts(text: str) -> dict[str, int]:
    return {
        "word_count": word_count(text),
        "char_count": char_count(text),
    }
