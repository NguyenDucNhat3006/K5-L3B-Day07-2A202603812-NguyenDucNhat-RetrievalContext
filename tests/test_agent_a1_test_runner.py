"""Offline guards for the one-shot A1 test runner."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))

from retrieval_v2 import approved_rows
from run_agent_a1_test import BudgetedClient, LOCK_MANIFEST, TEST_BENCHMARK, load_test_cases


class FakeClient:
    base_url = "https://openrouter.ai/api/v1"
    def __init__(self):
        self.calls = 0
    def complete(self, messages, **kwargs):
        self.calls += 1
        return {"choices": [{"message": {"content": "{}"}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2,
                          "total_tokens": 6, "cost": 0.000001}}


class FinalTestRunnerTests(unittest.TestCase):
    def test_locked_test_shape_and_gold_validate_without_retrieval(self):
        rows, _ = approved_rows()
        manifest = json.loads(LOCK_MANIFEST.read_text(encoding="utf-8-sig"))
        cases, digest = load_test_cases(TEST_BENCHMARK, rows, manifest["test"]["sha256"])
        self.assertEqual(len(cases), 7)
        self.assertEqual(sum(c["answerable"] for c in cases), 5)
        self.assertEqual(sum(not c["answerable"] for c in cases), 2)
        self.assertEqual(digest, manifest["test"]["sha256"])

    def test_budget_guard_stops_before_exceeding_call_or_token_caps(self):
        fake = FakeClient()
        guarded = BudgetedClient(fake, {"max_api_calls": 1, "max_total_tokens": 10,
            "max_cost_usd": 0.10}, (0.042, 0.184))
        with self.assertRaisesRegex(RuntimeError, "token reserve"):
            guarded.complete([{"role": "user", "content": "x" * 30}], max_tokens=5)
        self.assertEqual(fake.calls, 0)
        self.assertEqual(guarded.calls, 0)

    def test_budget_guard_records_usage_and_actual_cost_without_retry(self):
        fake = FakeClient()
        guarded = BudgetedClient(fake, {"max_api_calls": 1, "max_total_tokens": 100,
            "max_cost_usd": 0.10}, (0.042, 0.184))
        result = guarded.complete([{"role": "user", "content": "ok"}], max_tokens=10)
        self.assertEqual(fake.calls, 1)
        self.assertEqual(guarded.calls, 1)
        self.assertEqual(guarded.known_tokens, 6)
        self.assertAlmostEqual(guarded.actual_cost, 0.000001)
        self.assertEqual(result["usage"]["total_tokens"], 6)


if __name__ == "__main__":
    unittest.main()
