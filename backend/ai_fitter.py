import importlib
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv

from fit_checker import FitCheck, FitConstraints, check_fit

load_dotenv()

MAX_ATTEMPTS = 4
AI_PROVIDER = os.getenv("AI_PROVIDER", "nvidia").lower()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2048"))


@dataclass
class FitAttempt:
    result: str
    word_count: int
    char_count: int
    attempt: int
    met_target: bool
    revision_summary: list[str]


def fit_text(text: str, constraints: FitConstraints) -> FitAttempt:
    original_check = check_fit(text, constraints)
    if original_check.met_target:
        return FitAttempt(
            result=text,
            word_count=original_check.word_count,
            char_count=original_check.char_count,
            attempt=0,
            met_target=True,
            revision_summary=["No changes needed; the original text already met the target."],
        )

    client = _create_ai_client()
    try:
        current_words = original_check.word_count
        current_chars = original_check.char_count
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
            response_text = _call_ai(client, messages, role="writer")
            result = _extract_final_text(response_text)
            check = check_fit(result, constraints)

            attempt = FitAttempt(
                result=result,
                word_count=check.word_count,
                char_count=check.char_count,
                attempt=attempt_number,
                met_target=check.met_target,
                revision_summary=[],
            )

            if check.met_target:
                attempt.revision_summary = _summarize_revision(client, text, result, constraints, check)
                return attempt

            if best_attempt is None or _miss_size(attempt, constraints) < _miss_size(best_attempt, constraints):
                best_attempt = attempt

            if attempt_number < MAX_ATTEMPTS:
                feedback = _call_checker(client, text, result, check, constraints)
                messages.append({"role": "assistant", "content": result})
                messages.append({"role": "user", "content": _retry_prompt(feedback, check)})

        if best_attempt is None:
            return FitAttempt(
                text,
                current_words,
                current_chars,
                0,
                _meets_target(current_words, current_chars, constraints),
                ["No AI revision was returned."],
            )

        best_attempt.met_target = False
        best_check = check_fit(best_attempt.result, constraints)
        best_attempt.revision_summary = _summarize_revision(
            client,
            text,
            best_attempt.result,
            constraints,
            best_check,
        )
        return best_attempt
    finally:
        _close_ai_client(client)


def _create_ai_client() -> Any:
    if AI_PROVIDER == "anthropic":
        try:
            anthropic_module = importlib.import_module("anthropic")
        except ModuleNotFoundError as exc:
            raise RuntimeError("The 'anthropic' package is not installed. Run 'pip install -r requirements.txt' before using AI_PROVIDER=anthropic.") from exc

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to backend/.env before using /fit.")
        return anthropic_module.Anthropic(api_key=api_key)

    if AI_PROVIDER == "nvidia":
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is not set. Add it to backend/.env before using /fit.")
        return httpx.Client(
            base_url=NVIDIA_BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=120,
        )

    raise RuntimeError("AI_PROVIDER must be either 'nvidia' or 'anthropic'.")


def _call_ai(client: Any, messages: list[dict[str, str]], *, role: str) -> str:
    if AI_PROVIDER == "anthropic":
        return _call_claude(client, messages, role=role)
    return _call_nvidia(client, messages, role=role)


def _close_ai_client(client: Any) -> None:
    close = getattr(client, "close", None)
    if callable(close):
        close()


def _call_claude(client: Any, messages: list[dict[str, str]], *, role: str) -> str:
    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=_temperature_for_role(role),
        messages=messages,
    )
    return "".join(block.text for block in message.content if getattr(block, "type", None) == "text").strip()


def _call_nvidia(client: httpx.Client, messages: list[dict[str, str]], *, role: str) -> str:
    response = client.post(
        "/chat/completions",
        json={
            "model": NVIDIA_MODEL,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
            "temperature": _temperature_for_role(role),
            "stream": False,
        },
    )
    response.raise_for_status()
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"NVIDIA response did not include generated text: {data}") from exc


def _temperature_for_role(role: str) -> float:
    return 0.1 if role == "checker" else 0.3


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

    return f"""You are TextFitAI's writer agent. Your only job is to produce the revised text.

Python-computed current count:
- Words: {current_words}
- Characters: {current_chars}

Exact target:
{target_summary}

Required direction: {direction}
{direction_rules[direction]}

Output rules:
- Return only the final revised text.
- Do not include analysis, candidate cuts, labels, markdown, bullets, or word counts.
- Do not wrap the final revised text in quotes unless the quote marks are part of the user's text.
- Do not rely on your own word count. A Python checker will count the output after you respond.

Text to revise:
\"\"\"{text}\"\"\""""


def _call_checker(
    client: Any,
    original_text: str,
    attempted_text: str,
    check: FitCheck,
    constraints: FitConstraints,
) -> str:
    messages = [
        {
            "role": "user",
            "content": _checker_prompt(
                original_text=original_text,
                attempted_text=attempted_text,
                check=check,
                constraints=constraints,
            ),
        }
    ]
    return _call_ai(client, messages, role="checker")


def _checker_prompt(
    *,
    original_text: str,
    attempted_text: str,
    check: FitCheck,
    constraints: FitConstraints,
) -> str:
    misses = "\n".join(f"- {miss}" for miss in check.misses) or "- none"

    return f"""You are TextFitAI's checker agent. Python has already counted the writer output.

Do not calculate counts yourself. Use only these Python-computed facts:
- Words: {check.word_count}
- Characters: {check.char_count}
- Target met: {check.met_target}
- Misses:
{misses}

Exact target:
{_target_summary(constraints)}

Write concise feedback for the writer agent. Tell it exactly how to revise the attempted text to satisfy the Python-computed target while preserving the original meaning, tone, facts, and important qualifications.

Original text:
\"\"\"{original_text}\"\"\"

Writer attempt:
\"\"\"{attempted_text}\"\"\""""


def _summarize_revision(
    client: Any,
    original_text: str,
    final_text: str,
    constraints: FitConstraints,
    check: FitCheck,
) -> list[str]:
    if original_text.strip() == final_text.strip():
        return ["No wording changes were needed; the text already met the target."]

    messages = [
        {
            "role": "user",
            "content": _summary_prompt(
                original_text=original_text,
                final_text=final_text,
                constraints=constraints,
                check=check,
            ),
        }
    ]

    try:
        raw_summary = _call_ai(client, messages, role="checker")
    except Exception:
        return ["Revised the text to better match the target while preserving the original meaning."]

    return _parse_summary_bullets(raw_summary)


def _summary_prompt(
    *,
    original_text: str,
    final_text: str,
    constraints: FitConstraints,
    check: FitCheck,
) -> str:
    return f"""You are TextFitAI's revision summary agent.

Compare the original text to the final accepted text. Return 2-4 concise bullet points explaining what was cut, added, condensed, or reworded.

Rules:
- Do not include the final revised text.
- Do not include counts except when useful.
- Do not mention internal agents or prompts.
- Return bullets only.

Exact target:
{_target_summary(constraints)}

Python-verified final counts:
- Words: {check.word_count}
- Characters: {check.char_count}
- Target met: {check.met_target}

Original text:
\"\"\"{original_text}\"\"\"

Final accepted text:
\"\"\"{final_text}\"\"\""""


def _parse_summary_bullets(raw_summary: str) -> list[str]:
    bullets = []
    for line in raw_summary.splitlines():
        item = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if item:
            bullets.append(item)

    if not bullets:
        return ["Revised the text to better match the target while preserving the original meaning."]

    return bullets[:4]


def _retry_prompt(feedback: str, check: FitCheck) -> str:
    misses = "\n".join(f"- {miss}" for miss in check.misses) or "- none"

    return f"""The Python checker rejected your last output.

Python-computed counts:
- Words: {check.word_count}
- Characters: {check.char_count}
- Misses:
{misses}

Checker feedback:
{feedback}

Revise again. Return only the final revised text. Do not include analysis, labels, markdown, counts, or quotes around the whole answer."""


def _extract_final_text(response_text: str) -> str:
    text = response_text.strip()
    marker_match = re.search(r"(?im)^\s*-{0,3}\s*final\s*-{0,3}\s*$", text)
    if marker_match:
        text = text[marker_match.end() :].strip()

    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()

    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()

    return text


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
