import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from ai_fitter import _extract_final_text, fit_text  # noqa: E402
from counters import char_count, counts, word_count  # noqa: E402
from fit_checker import FitConstraints, check_fit  # noqa: E402
from main import FitRequest  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
