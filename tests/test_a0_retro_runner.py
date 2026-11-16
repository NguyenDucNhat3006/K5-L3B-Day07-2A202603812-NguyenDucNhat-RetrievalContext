from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))

from run_agent_a0_retro_test import GuardedClient, retrieval_metrics


class FakeClient:
    base_url = "https://openrouter.ai/api/v1"

    def __init__(self):
        self.calls = 0

    def complete(self, messages, *, tools=None, max_tokens=400, json_mode=False):
        self.calls += 1
        return {"id": f"fake-{self.calls}", "model": "fake-model",
                "choices": [{"message": {"content": "ok", "tool_calls": None}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                          "total_tokens": 15, "cost": 0.000001},
                "openrouter_metadata": {"endpoints": {"available": []}}}


class A0RetrospectiveRunnerTests(unittest.TestCase):
    def test_guarded_client_tracks_usage_and_never_exceeds_call_cap(self):
        fake = FakeClient()
        with patch.dict("run_agent_a0_retro_test.RUN_LIMITS", {"max_api_calls": 1,
                    "max_total_tokens": 2000, "max_cost_usd": 0.10}):
            guarded = GuardedClient(fake, (0.042, 0.184))
            guarded.complete([{"role": "user", "content": "short"}], max_tokens=300)
            with self.assertRaisesRegex(RuntimeError, "hard cap"):
                guarded.complete([{"role": "user", "content": "short"}], max_tokens=300)
        self.assertEqual(fake.calls, 1)
        self.assertEqual(guarded.total_tokens, 15)
        self.assertAlmostEqual(guarded.actual_cost_total, 0.000001)

    def test_token_reservation_stops_before_network_call(self):
        fake = FakeClient()
        with patch.dict("run_agent_a0_retro_test.RUN_LIMITS", {"max_api_calls": 14,
                    "max_total_tokens": 10, "max_cost_usd": 0.10}):
            guarded = GuardedClient(fake, (0.042, 0.184))
            with self.assertRaisesRegex(RuntimeError, "token reserve"):
                guarded.complete([{"role": "user", "content": "question"}], max_tokens=300)
        self.assertEqual(fake.calls, 0)
        self.assertEqual(guarded.calls, 0)

    def test_retrieval_metrics_require_gold_text_in_final_context(self):
        case = {"id": "t1", "answerable": True,
                "gold": [{"chunk_id": "doc:p1:c1", "source_id": "doc", "page": 1,
                          "evidence": "alpha beta"}]}
        hit = {"id": "doc:p1:c1", "source_id": "doc", "page": 1,
               "text": "alpha\nbeta"}
        trace = {"query_id": "t1", "status": "answered", "retrieval_hits": [hit],
                 "context_ids": ["doc:p1:c1"], "selected_context": "alpha beta"}
        metrics = retrieval_metrics([case], [trace])
        self.assertEqual(metrics["hit_at_1"]["count"], 1)
        self.assertEqual(metrics["evidence_hit_at_3"]["count"], 1)
        self.assertEqual(metrics["context_evidence_rate"]["count"], 1)
        trace["selected_context"] = "alpha only"
        self.assertEqual(retrieval_metrics([case], [trace])["context_evidence_rate"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
