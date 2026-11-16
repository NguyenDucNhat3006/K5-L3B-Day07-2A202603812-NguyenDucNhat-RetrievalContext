"""Offline controller/tool/citation checks; no model quality claims."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter"))
from agent_v2 import OpenRouterChatClient, run_v2_agent, validate_answer
from run_agent_v2_dev import load_local_env, metrics

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
    def test_openrouter_payload_routing_usage_and_actual_provider(self):
        final = {"status": "abstain", "answer": "", "citations": []}
        first = {"id": "gen1", "model": "z-ai/glm-5.3-flash", "choices": [{"message": {"tool_calls": [CALL]}}],
                 "openrouter_metadata": {"endpoints": {"available": [{"provider": "ProviderA", "selected": True}]}},
                 "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": 0.00001}}
        second = {"id": "gen2", "model": "z-ai/glm-5.3-flash", "choices": [{"message": {"content": json.dumps(final)}}],
                  "openrouter_metadata": {"endpoints": {"available": [{"provider": "ProviderB", "selected": True}]}},
                  "usage": {"prompt_tokens": 20, "completion_tokens": 5, "total_tokens": 25, "cost": 0.00002}}
        requests = []
        class Response:
            def __init__(self, data): self.data = data
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args): return json.dumps(self.data).encode()
        responses = iter((first, second))
        def fake_urlopen(request, timeout):
            requests.append(request)
            return Response(next(responses))
        client = OpenRouterChatClient("z-ai/glm-5.3-flash:floor", "secret", max_price=(0.0399, 0.0784))
        with patch("agent_v2.urlopen", fake_urlopen):
            trace = run_v2_agent("q", Suite(), client)
        body = json.loads(requests[0].data)
        self.assertEqual(body["model"], "z-ai/glm-5.3-flash:floor")
        self.assertEqual(body["provider"]["max_price"], {"prompt": 0.0399, "completion": 0.0784})
        self.assertTrue(body["provider"]["require_parameters"])
        self.assertTrue(body["usage"]["include"])
        self.assertEqual(json.loads(requests[1].data)["response_format"], {"type": "json_object"})
        self.assertEqual([item["provider"] for item in trace["api_responses"]], ["ProviderA", "ProviderB"])
        self.assertEqual(trace["actual_cost_usd"], 0.00003)
        self.assertEqual(trace["token_usage"]["total_tokens"], 40)

    def test_dotenv_loader_does_not_override_process_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            env = Path(folder) / ".env"
            env.write_text("\ufeffOPENROUTER_API_KEY=file-secret\nLAB07_LLM_MODEL=z-ai/glm-5.3-flash:floor\n", encoding="utf-8")
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "process-secret"}, clear=True):
                load_local_env(env)
                self.assertEqual(os.environ["OPENROUTER_API_KEY"], "process-secret")
                self.assertEqual(os.environ["LAB07_LLM_MODEL"], "z-ai/glm-5.3-flash:floor")

    def test_one_case_metrics(self):
        final = {"status": "answered", "answer": "11 cách [c1]", "citations": [{"chunk_id": "c1", "source": "chapter2.pdf", "page": 29}]}
        trace = run_v2_agent("q", Suite(), Client(final))
        trace["query_id"] = "d01"
        summary = metrics([{"id": "d01", "answerable": True}], [trace])
        self.assertEqual(summary["cases"], 1)
        self.assertEqual(summary["citation_structure_valid"], 1)
        self.assertEqual(summary["grounded_answer"], "requires_manual_review")

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
