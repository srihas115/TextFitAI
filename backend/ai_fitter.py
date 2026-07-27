import os
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

from counters import char_count, word_count

load_dotenv()

MAX_ATTEMPTS = 4
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")


@dataclass
class FitConstraints:
    min_words: Optional[int] = None
    max_words: Optional[int] = None
    min_chars: Optional[int] = None
    max_chars: Optional[int] = None


@dataclass
class FitAttempt:
    result: str
    word_count: int
    char_count: int
    attempt: int
    met_target: bool


def fit_text(text: str, constraints: FitConstraints) -> FitAttempt:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to backend/.env before using /fit.")

    client = Anthropic(api_key=api_key)
    current_words = word_count(text)
    current_chars = char_count(text)
    direction = _direction(current_words, current_chars, constraints)
    target_summary = _target_summary(constraints)

    messages = [
        {
            "role": "user",
            "content": _initial_prompt(
                text=text,
                current_words=current_words,
                current_chars=current_chars,
                direction=direction,
                target_summary=target_summary,
            ),
        }
    ]

    best_attempt: FitAttempt | None = None

    for attempt_number in range(1, MAX_ATTEMPTS + 1):
        response_text = _call_claude(client, messages)
        result = _extract_final_text(response_text)
        result_words = word_count(result)
        result_chars = char_count(result)
        met_target = _meets_target(result_words, result_chars, constraints)

        attempt = FitAttempt(
            result=result,
            word_count=result_words,
            char_count=result_chars,
            attempt=attempt_number,
            met_target=met_target,
        )

        if met_target:
            return attempt

        if best_attempt is None or _miss_size(attempt, constraints) < _miss_size(best_attempt, constraints):
            best_attempt = attempt

        if attempt_number < MAX_ATTEMPTS:
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": _retry_prompt(attempt, constraints)})

    if best_attempt is None:
        return FitAttempt(text, current_words, current_chars, 0, _meets_target(current_words, current_chars, constraints))

    best_attempt.met_target = False
    return best_attempt


def _call_claude(client: Anthropic, messages: list[dict[str, str]]) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        temperature=0.3,
        messages=messages,
    )
    return "".join(block.text for block in message.content if getattr(block, "type", None) == "text").strip()


def _initial_prompt(
    *,
    text: str,
    current_words: int,
    current_chars: int,
    direction: str,
    target_summary: str,
) -> str:
    direction_rules = {
        "shorten": (
            "Shorten the text by removing filler, redundant modifiers, hedging language, "
            "and throat-clearing phrases. Never drop distinct claims, facts, names, numbers, "
            "or important qualifications."
        ),
        "lengthen": (
            "Lengthen the text by adding supporting detail, clarification, or concrete examples "
            "to existing points. Do not repeat sentences, pad with fluff, or introduce unrelated claims."
        ),
        "fit": (
            "Revise only as much as needed to satisfy the target. Preserve the user's meaning, tone, "
            "claims, facts, and structure wherever possible."
        ),
    }

    return f"""You are Fitto, an AI text fitting editor.

Current count:
- Words: {current_words}
- Characters: {current_chars}

Exact target:
{target_summary}

Required direction: {direction}
{direction_rules[direction]}

First list 3-5 candidate cuts or additions that would help hit the target.
Then write a line containing exactly:
---FINAL---
After that marker, produce ONLY the final revised text and nothing else.

Text to revise:
\"\"\"{text}\"\"\""""


def _retry_prompt(attempt: FitAttempt, constraints: FitConstraints) -> str:
    misses = []

    if constraints.max_words is not None and attempt.word_count > constraints.max_words:
        over = attempt.word_count - constraints.max_words
        misses.append(f"Your last attempt was {attempt.word_count} words, {over} over the {constraints.max_words} max. Cut about {over} more words without losing meaning.")
    if constraints.min_words is not None and attempt.word_count < constraints.min_words:
        under = constraints.min_words - attempt.word_count
        misses.append(f"Your last attempt was {attempt.word_count} words, {under} under the {constraints.min_words} min. Add about {under} more words with useful detail and no repetition.")
    if constraints.max_chars is not None and attempt.char_count > constraints.max_chars:
        over = attempt.char_count - constraints.max_chars
        misses.append(f"Your last attempt was {attempt.char_count} characters, {over} over the {constraints.max_chars} max. Cut about {over} more characters without losing meaning.")
    if constraints.min_chars is not None and attempt.char_count < constraints.min_chars:
        under = constraints.min_chars - attempt.char_count
        misses.append(f"Your last attempt was {attempt.char_count} characters, {under} under the {constraints.min_chars} min. Add about {under} more characters with useful detail and no repeated sentences.")

    return "\n".join(misses) + "\nReturn the revised text after a line containing exactly ---FINAL---."


def _extract_final_text(response_text: str) -> str:
    marker = "---FINAL---"
    if marker not in response_text:
        return response_text.strip()
    return response_text.split(marker, 1)[1].strip()


def _direction(words: int, chars: int, constraints: FitConstraints) -> str:
    if (constraints.max_words is not None and words > constraints.max_words) or (
        constraints.max_chars is not None and chars > constraints.max_chars
    ):
        return "shorten"
    if (constraints.min_words is not None and words < constraints.min_words) or (
        constraints.min_chars is not None and chars < constraints.min_chars
    ):
        return "lengthen"
    return "fit"


def _target_summary(constraints: FitConstraints) -> str:
    parts = []
    if constraints.min_words is not None:
        parts.append(f"- Minimum words: {constraints.min_words}")
    if constraints.max_words is not None:
        parts.append(f"- Maximum words: {constraints.max_words}")
    if constraints.min_chars is not None:
        parts.append(f"- Minimum characters: {constraints.min_chars}")
    if constraints.max_chars is not None:
        parts.append(f"- Maximum characters: {constraints.max_chars}")
    return "\n".join(parts) if parts else "- No explicit limits. Preserve the text."


def _meets_target(words: int, chars: int, constraints: FitConstraints) -> bool:
    if constraints.min_words is not None and words < constraints.min_words:
        return False
    if constraints.max_words is not None and words > constraints.max_words:
        return False
    if constraints.min_chars is not None and chars < constraints.min_chars:
        return False
    if constraints.max_chars is not None and chars > constraints.max_chars:
        return False
    return True


def _miss_size(attempt: FitAttempt, constraints: FitConstraints) -> int:
    miss = 0
    if constraints.min_words is not None and attempt.word_count < constraints.min_words:
        miss += constraints.min_words - attempt.word_count
    if constraints.max_words is not None and attempt.word_count > constraints.max_words:
        miss += attempt.word_count - constraints.max_words
    if constraints.min_chars is not None and attempt.char_count < constraints.min_chars:
        miss += constraints.min_chars - attempt.char_count
    if constraints.max_chars is not None and attempt.char_count > constraints.max_chars:
        miss += attempt.char_count - constraints.max_chars
    return miss
