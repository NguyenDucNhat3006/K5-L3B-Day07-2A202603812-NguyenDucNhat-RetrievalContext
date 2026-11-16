"""Offline controller/tool/citation checks; no model quality claims."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter"))
from agent_v2 import run_v2_agent, validate_answer

HIT = {"id": "c1", "chunk_id": "c1", "text": "Có 11 cách chọn áo.",
       "source_id": "chapter2", "source": "chapter2.pdf", "page": 29,
       "metadata": {"extraction_quality": "needs_review", "quality_reasons": ["table_layout_review"]},
       "rank": 1, "score": 0.8}
CALL = {"id": "call1", "type": "function", "function": {"name": "search_discrete_math", "arguments": "{}"}}


class Suite:
    def __init__(self, hits=None):
        self.hits = [HIT] if hits is None else hits
        self.calls = []

    def tfidf(self, question, *, filters, top_k):
        self.calls.append((question, filters, top_k))
        return self.hits


class Client:
    def __init__(self, final, search=True):
        self.final, self.search, self.calls = final, search, []

    def complete(self, messages, *, tools=None, max_tokens=400, json_mode=False):
        self.calls.append((messages, tools, json_mode))
        message = ({"tool_calls": [CALL]} if self.search else {"content": "I know"}) if tools else {"content": json.dumps(self.final, ensure_ascii=False)}
        return {"choices": [{"message": message}], "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


class AgentV2Tests(unittest.TestCase):
    def test_real_tool_protocol_and_c0_citations(self):
        final = {"status": "answered", "answer": "Có 11 cách [c1]", "citations": [{"chunk_id": "c1", "source": "chapter2.pdf", "page": 29}]}
        suite, client = Suite(), Client(final)
        trace = run_v2_agent("Có mấy cách?", suite, client)
        self.assertEqual(trace["status"], "answered")
        self.assertEqual(suite.calls, [("Có mấy cách?", None, 3)])
        self.assertEqual(trace["controller_decision"], "search")
        self.assertIn("extraction_quality=needs_review", trace["selected_context"])
        self.assertLessEqual(len(trace["selected_context"]), 800)
        self.assertEqual(trace["token_usage"]["total_tokens"], 30)
        self.assertTrue(client.calls[1][2])

    def test_fabricated_and_wrong_page_citations_rejected(self):
        for citation in ({"chunk_id": "fake", "source": "chapter2.pdf", "page": 29},
                         {"chunk_id": "c1", "source": "chapter2.pdf", "page": 30}):
            final = {"status": "answered", "answer": f"11 cách [{citation['chunk_id']}]", "citations": [citation]}
            self.assertEqual(run_v2_agent("q", Suite(), Client(final))["status"], "abstain")

    def test_missing_evidence_abstention(self):
        for question in ("d16: áo nào đắt hơn?", "d17: Dijkstra mất bao nhiêu mili giây?"):
            trace = run_v2_agent(question, Suite(), Client({"status": "abstain", "answer": "", "citations": []}))
            self.assertEqual(trace["status"], "abstain")
            self.assertEqual(trace["reason"], "model_abstained")

    def test_no_search_is_recorded_and_refused(self):
        suite = Suite()
        trace = run_v2_agent("q", suite, Client({}, search=False))
        self.assertEqual(trace["status"], "abstain")
        self.assertEqual(trace["reason"], "no_search")
        self.assertEqual(suite.calls, [])

    def test_uncited_sentence_rejected(self):
        valid, reason = validate_answer("11 cách [c1]. Giá cao hơn.",
            [{"chunk_id": "c1", "source": "chapter2.pdf", "page": 29}], [HIT])
        self.assertFalse(valid)
        self.assertEqual(reason, "uncited_sentence")


if __name__ == "__main__":
    unittest.main()
