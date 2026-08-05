import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from ai_fitter import _extract_final_text, fit_text  # noqa: E402
from counters import char_count, counts, word_count  # noqa: E402
from fit_checker import FitConstraints, check_fit  # noqa: E402
from main import FitRequest, app, get_brand_suffix  # noqa: E402
from one_word_summarizer import OneWordSummary, _extract_one_word, summarize_to_one_word  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402


class CounterTests(unittest.TestCase):
    def test_counts_match_documented_rules(self) -> None:
        text = "  One\t two\nthree  "

        self.assertEqual(word_count(text), 3)
        self.assertEqual(char_count(text), len(text))
        self.assertEqual(counts(text), {"word_count": 3, "char_count": len(text)})


class FitCheckerTests(unittest.TestCase):
    def test_reports_all_constraint_misses(self) -> None:
        result = check_fit("tiny", FitConstraints(min_words=2, min_chars=10))

        self.assertFalse(result.met_target)
        self.assertEqual(result.word_count, 1)
        self.assertEqual(result.char_count, 4)
        self.assertEqual(
            result.misses,
            [
                "1 words under the 2 minimum",
                "6 characters under the 10 minimum",
            ],
        )


class RequestValidationTests(unittest.TestCase):
    def test_omitted_constraints_stay_unbounded(self) -> None:
        request = FitRequest(text="Already fine.")

        self.assertIsNone(request.min_words)
        self.assertIsNone(request.max_words)
        self.assertIsNone(request.min_chars)
        self.assertIsNone(request.max_chars)


class AppConfigTests(unittest.TestCase):
    def test_brand_suffix_is_dev_preview_only_on_dev_branch(self) -> None:
        self.assertEqual(get_brand_suffix("dev"), "(dev preview)")
        self.assertEqual(get_brand_suffix("main"), "(beta)")

    def test_app_config_uses_deployment_branch_env(self) -> None:
        with patch.dict("os.environ", {"VERCEL_GIT_COMMIT_REF": "main"}, clear=False):
            response = TestClient(app).get("/app-config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["brand_suffix"], "(beta)")


class AiFitterTests(unittest.TestCase):
    def test_no_constraints_returns_without_ai_call(self) -> None:
        result = fit_text("No target means no revision.", FitConstraints())

        self.assertEqual(result.result, "No target means no revision.")
        self.assertEqual(result.attempt, 0)
        self.assertTrue(result.met_target)
        self.assertEqual(result.revision_summary, ["No changes needed"])

    def test_extract_final_text_handles_common_wrappers(self) -> None:
        self.assertEqual(_extract_final_text("---FINAL---\nRevised text"), "Revised text")
        self.assertEqual(_extract_final_text("```\nRevised text\n```"), "Revised text")
        self.assertEqual(_extract_final_text('"Revised text"'), "Revised text")


class OneWordSummarizerTests(unittest.TestCase):
    def test_extract_one_word_strips_labels_and_extra_words(self) -> None:
        self.assertEqual(_extract_one_word("Summary: quiet confidence", fallback_text="unused"), "quiet")

    def test_summarizes_once_and_returns_strict_one_word(self) -> None:
        import one_word_summarizer

        calls = []

        def fake_create_client() -> object:
            return object()

        def fake_call_ai(client: object, messages: list[dict[str, str]], *, role: str) -> str:
            calls.append((client, messages, role))
            return "Summary: momentum and clarity"

        original_create_client = one_word_summarizer._create_ai_client
        original_call_ai = one_word_summarizer._call_ai
        original_close_client = one_word_summarizer._close_ai_client
        one_word_summarizer._create_ai_client = fake_create_client
        one_word_summarizer._call_ai = fake_call_ai
        one_word_summarizer._close_ai_client = lambda client: None

        try:
            result = summarize_to_one_word(
                "The team found a clear path forward after the launch.",
                FitConstraints(min_words=1, max_words=1),
            )
        finally:
            one_word_summarizer._create_ai_client = original_create_client
            one_word_summarizer._call_ai = original_call_ai
            one_word_summarizer._close_ai_client = original_close_client

        self.assertEqual(result.result, "momentum")
        self.assertEqual(result.word_count, 1)
        self.assertEqual(result.attempt, 1)
        self.assertTrue(result.met_target)
        self.assertEqual(len(calls), 1)


class FitEndpointTests(unittest.TestCase):
    def test_exact_one_word_limits_use_secret_summarizer(self) -> None:
        import main

        calls = []

        def fake_summarize(text: str, constraints: FitConstraints) -> OneWordSummary:
            calls.append((text, constraints))
            return OneWordSummary(
                result="Focus",
                word_count=1,
                char_count=5,
                attempt=1,
                met_target=True,
                revision_summary=["Secret one-word summary"],
            )

        original_summarize = main.summarize_to_one_word
        main.summarize_to_one_word = fake_summarize

        try:
            response = TestClient(app).post(
                "/fit",
                json={
                    "text": "Please condense this whole idea into one strong concept.",
                    "min_words": 1,
                    "max_words": 1,
                },
            )
        finally:
            main.summarize_to_one_word = original_summarize

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "Focus")
        self.assertEqual(response.json()["attempts"], 1)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
