"""A1 formatting and bounded single-repair tests; no API calls."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter"))
from agent_a1 import run_a1_agent
from test_agent_v2 import HIT, CALL, Suite


def response(message, cost=0.00001):
    return {"id":"mock","model":"mock-model","choices":[{"message":message}],
            "usage":{"prompt_tokens":10,"completion_tokens":5,"total_tokens":15,"cost":cost}}


class SequenceClient:
    def __init__(self, outputs): self.outputs, self.calls = iter(outputs), []
    def complete(self, messages, *, tools=None, max_tokens=400, json_mode=False):
        self.calls.append({"messages":messages,"tools":tools,"json_mode":json_mode})
        return next(self.outputs)


class A1Tests(unittest.TestCase):
    def outputs(self, final, repair=None):
        result=[response({"tool_calls":[CALL]}),response({"content":final})]
        if repair is not None: result.append(response({"content":repair}))
        return result

    def final(self, *, answer="11 cách [c1]", citation=None, status="answered"):
        return json.dumps({"status":status,"answer":answer,
            "citations": ([citation or {"chunk_id":"c1","source":"chapter2.pdf","page":29}] if status=="answered" else [])},ensure_ascii=False)

    def test_inline_citation_and_exact_metadata_pass(self):
        t=run_a1_agent("q",Suite(),SequenceClient(self.outputs(self.final())))
        self.assertEqual(t["status"],"answered")
        self.assertEqual(t["citations"][0]["page"],29)
        self.assertEqual(t["repair_count"],0)

    def test_invalid_json_gets_only_one_repair(self):
        c=SequenceClient(self.outputs("not json",self.final()))
        t=run_a1_agent("q",Suite(),c)
        self.assertEqual(t["status"],"answered")
        self.assertEqual(t["repair_count"],1)
        self.assertEqual(len(c.calls),3)
        self.assertTrue(c.calls[-1]["json_mode"])
        self.assertIn("CONTEXT (unchanged)",c.calls[-1]["messages"][-1]["content"])

    def test_missing_inline_citation_repaired_once(self):
        c=SequenceClient(self.outputs(self.final(answer="Có 11 cách."),self.final()))
        t=run_a1_agent("q",Suite(),c)
        self.assertEqual(t["status"],"answered")
        self.assertEqual(t["repair_count"],1)

    def test_nonexistent_citation_cannot_pass_or_auto_create(self):
        invalid=self.final(answer="11 cách [made-up]",citation={"chunk_id":"made-up","source":"chapter2.pdf","page":29})
        t=run_a1_agent("q",Suite(),SequenceClient(self.outputs(invalid,invalid)))
        self.assertEqual(t["status"],"abstain")
        self.assertEqual(t["failure_type"],"repair_failure")
        self.assertEqual(t["citations"],[])
        self.assertEqual(t["repair_count"],1)

    def test_source_or_page_mismatch_does_not_pass(self):
        for citation in ({"chunk_id":"c1","source":"wrong.pdf","page":29},
                         {"chunk_id":"c1","source":"chapter2.pdf","page":3}):
            invalid=self.final(answer="11 cách [c1]",citation=citation)
            t=run_a1_agent("q",Suite(),SequenceClient(self.outputs(invalid,invalid)))
            self.assertEqual(t["status"],"abstain")
            self.assertEqual(t["failure_type"],"repair_failure")

    def test_no_retrieved_evidence_abstains_as_retrieval_failure(self):
        t=run_a1_agent("q",Suite([]),SequenceClient([response({"tool_calls":[CALL]})]))
        self.assertEqual(t["failure_type"],"retrieval_failure")
        self.assertEqual(t["status"],"abstain")

    def test_explicit_abstention_is_not_repaired(self):
        final=self.final(status="abstain",answer="")
        c=SequenceClient(self.outputs(final))
        t=run_a1_agent("q",Suite(),c)
        self.assertEqual(t["failure_type"],"model_abstention")
        self.assertEqual(len(c.calls),2)
        self.assertEqual(t["repair_count"],0)

    def test_repair_failure_is_bounded_to_one(self):
        c=SequenceClient(self.outputs("{}","still invalid"))
        t=run_a1_agent("q",Suite(),c)
        self.assertEqual(t["failure_type"],"repair_failure")
        self.assertEqual(len(c.calls),3)
        self.assertEqual(t["repair_count"],1)


if __name__=="__main__": unittest.main()
