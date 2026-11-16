"""Context packing keeps full citations and never receives gold evidence."""

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))

from context_engineering_v2 import (
    RETRIEVAL_TRACES, citation_block, frozen_tfidf_traces, pack_c0, pack_c1, review_risk,
    run_contexts,
)
from evaluate_retrieval_v2 import load_dev_benchmark
from retrieval_v2 import approved_rows
from summarize_context_review_v2 import AUDIT, RUN, summarize


def hit(chunk_id, rank, text, quality="ok", reasons=None, content_type="definition"):
    return {"id": chunk_id, "chunk_id": chunk_id, "rank": rank, "text": text,
            "source_id": "doc", "source": "doc.pdf", "page": rank,
            "score": 1 / rank,
            "metadata": {"extraction_quality": quality,
                         "quality_reasons": reasons or [],
                         "content_type": content_type}}


class ContextPackingTests(unittest.TestCase):
    def test_c0_preserves_rank_full_text_citation_and_budget(self):
        hits = [hit("a", 1, "A" * 450), hit("b", 2, "B" * 150),
                hit("c", 3, "C" * 150)]
        context, ids = pack_c0(hits, budget_chars=800)
        self.assertEqual(ids, ["a", "b"])
        self.assertLessEqual(len(context), 800)
        self.assertIn(citation_block(hits[0]), context)
        self.assertIn(citation_block(hits[1]), context)
        self.assertIn("source=doc.pdf | page=1 | extraction_quality=ok", context)
        self.assertNotIn("C" * 150, context)

    def test_c1_selects_complete_units_without_gold(self):
        hits = [hit("a", 1, "A" * 600, "needs_review",
                    ["diagram_requires_visual_check"], "exercise"),
                hit("b", 2, "B" * 120), hit("c", 3, "C" * 120)]
        c0, ids0 = pack_c0(hits, budget_chars=800)
        c1, ids1 = pack_c1("Định nghĩa", hits, budget_chars=800)
        self.assertEqual(ids0, ["a"])
        self.assertEqual(ids1, ["b", "c"])
        self.assertLessEqual(len(c1), 800)
        self.assertIn("B" * 120, c1)
        self.assertIn("C" * 120, c1)
        self.assertNotIn("A" * 600, c1)
        self.assertNotEqual(c0, c1)
        # A gold label attached to a retrieval hit cannot influence selection.
        altered = [{**item, "gold_evidence_hit": item["id"] == "a"} for item in hits]
        self.assertEqual(pack_c1("Định nghĩa", altered, 800), (c1, ids1))

    def test_review_flag_is_not_equated_with_missing_evidence(self):
        readable = hit("a", 1, "Ví dụ: 5+6 =11", "needs_review",
                       ["table_columns_unreliable"], "example")
        missing_visual = hit("b", 2, "Hình 1", "needs_review",
                             ["diagram_requires_visual_check"], "exercise")
        self.assertEqual(review_risk(readable), "text_review")
        self.assertEqual(review_risk(missing_visual), "visual_or_math_review")
        self.assertIn("extraction_quality=needs_review", citation_block(readable))

    @unittest.skipUnless(RETRIEVAL_TRACES.is_file(), "local frozen retrieval trace absent")
    def test_locked_dev_trace_count_and_citation_integrity(self):
        rows, _ = approved_rows()
        questions, _ = load_dev_benchmark(ROOT / "data/benchmark_v2_dev.json", rows)
        tfidf, digest = frozen_tfidf_traces(questions, rows)
        self.assertEqual(len(tfidf), 17)
        self.assertEqual(len(digest), 64)
        self.assertTrue(all(trace["strategy"] == "tfidf" for trace in tfidf))

    def test_manual_metric_input_is_separate_from_packer(self):
        class SimpleTokenizer:
            @staticmethod
            def encode(value, **_kwargs):
                return list(value.split())

        hits = [hit("a", 1, "định nghĩa cây"), hit("b", 2, "đồ thị")]
        question = {"id": "d", "question": "định nghĩa cây", "answerable": True,
                    "gold": [{"chunk_id": "a", "source_id": "doc", "page": 1,
                              "evidence": "định nghĩa cây"}]}
        retrieval = {"query_id": "d", "results": hits, "retrieval_ms": 1.0}
        metrics, traces = run_contexts([question], [retrieval], SimpleTokenizer())
        self.assertEqual(len(traces), 2)
        self.assertTrue(all(trace["context_evidence"] for trace in traces))
        self.assertEqual(metrics["configs"]["C0"]["context_evidence_rate"]["total"], 1)
        self.assertTrue(all("extraction_quality=" in trace["context"] for trace in traces))

    @unittest.skipUnless((RUN / "traces.json").is_file(), "local context trace absent")
    def test_manual_review_is_complete_and_citations_are_valid(self):
        rows, _ = approved_rows()
        traces = json.loads((RUN / "traces.json").read_text(encoding="utf-8"))
        audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        result = summarize(audit, traces, rows)
        self.assertEqual(result["reviewed_contexts"], 34)
        self.assertEqual(result["configs"]["C0"]["manual_quality"]["grade_2"], 13)
        self.assertEqual(result["configs"]["C1"]["manual_quality"]["grade_1"], 1)
        tampered = copy.deepcopy(audit)
        tampered["cases"][0]["C0"]["support_ids"] = ["not-in-context"]
        with self.assertRaises(ValueError):
            summarize(tampered, traces, rows)


if __name__ == "__main__":
    unittest.main()
