"""One-shot secret feature for exact one-word summaries."""

from dataclasses import dataclass
import re

from ai_fitter import _call_ai, _close_ai_client, _create_ai_client
from fit_checker import FitConstraints, check_fit


@dataclass
class OneWordSummary:
    result: str
    word_count: int
    char_count: int
    attempt: int
    met_target: bool
    revision_summary: list[str]


def summarize_to_one_word(text: str, constraints: FitConstraints) -> OneWordSummary:
    """Summarize text into exactly one word without the multi-attempt fitter."""
    client = _create_ai_client()
    try:
        raw_summary = _call_ai(
            client,
            [{"role": "user", "content": _one_word_prompt(text)}],
            role="writer",
        )
    finally:
        _close_ai_client(client)

    result = _extract_one_word(raw_summary, fallback_text=text)
    check = check_fit(result, constraints)

    return OneWordSummary(
        result=result,
        word_count=check.word_count,
        char_count=check.char_count,
        attempt=1,
        met_target=check.met_target,
        revision_summary=["Secret one-word summary"],
    )


def _one_word_prompt(text: str) -> str:
    return f"""You are TextFitAI's secret one-word summarizer.

Summarize the entire user-provided text into exactly one word.

Rules:
- Return one single word only.
- No labels, punctuation, quotes, markdown, explanation, or word count.
- Choose the word that best captures the core meaning or feeling of the text.

Text:
\"\"\"{text}\"\"\""""


def _extract_one_word(response_text: str, *, fallback_text: str) -> str:
    text = response_text.strip()

    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()

    if ":" in text:
        text = text.rsplit(":", 1)[-1].strip()

    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()

    words = _word_candidates(text)
    if words:
        return words[0]

    fallback_words = _word_candidates(fallback_text)
    if fallback_words:
        return fallback_words[0]

    return "Summary"


def _word_candidates(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", text)
