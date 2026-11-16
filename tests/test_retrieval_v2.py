"""Unit and opt-in live checks for the read-only V2 retrieval experiment."""

import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))

from evaluate_retrieval_v2 import evidence_in_text, load_dev_benchmark, run_dev
from index_discrete_math_v2 import STRATEGY, database_snapshot
from retrieval_v2 import V2RetrievalSuite, _matches, approved_rows, live_suite


def row(chunk_id, text, chapter, quality="ok"):
    return {"id": chunk_id, "text": text, "source_id": "doc", "source": "doc.pdf",
            "page": chapter, "metadata": {"subject": "discrete_math", "chapter": chapter,
                                           "extraction_quality": quality}}


class FakeDense:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def search(self, query, *, filters, top_k):
        self.calls.append((query, filters, top_k))
        return [{**item, "score": 0.9 - index * 0.1}
                for index, item in enumerate(self.rows) if _matches(item, filters)][:top_k]


class RetrievalV2Tests(unittest.TestCase):
    def setUp(self):
        self.rows = [row("a", "đồ thị cây khung", 1),
                     row("b", "đồ thị có trọng số", 2, "needs_review"),
                     row("c", "quan hệ thứ tự", 3)]
        self.backend = FakeDense([self.rows[1], self.rows[0], self.rows[2]])
        self.suite = V2RetrievalSuite(self.rows, self.backend)

    def test_dense_tfidf_rrf_rank_and_canonical_metadata(self):
        dense = self.suite.dense("đồ thị", top_k=3)
        tfidf = self.suite.tfidf("đồ thị", top_k=3)
        hybrid = self.suite.hybrid("đồ thị", top_k=3, candidate_k=3, rrf_k=60)
        self.assertEqual([hit["id"] for hit in dense], ["b", "a", "c"])
        self.assertEqual([hit["id"] for hit in tfidf], ["a", "b"])
        self.assertEqual([hit["rank"] for hit in hybrid], [1, 2, 3])
        self.assertEqual([hit["score"] for hit in hybrid],
                         sorted((hit["score"] for hit in hybrid), reverse=True))
        for hit in hybrid:
            expected = (1 / (60 + hit["dense_rank"]) if hit["dense_rank"] else 0) + (
                1 / (60 + hit["tfidf_rank"]) if hit["tfidf_rank"] else 0)
            self.assertAlmostEqual(hit["score"], expected)
            self.assertEqual(hit["metadata"], self.suite.by_id[hit["id"]]["metadata"])
            self.assertEqual(hit["chunk_id"], hit["id"])
        self.assertEqual(self.suite.by_id["b"]["metadata"]["extraction_quality"], "needs_review")

    def test_filters_and_no_results_for_all_methods(self):
        for method in ("dense", "tfidf", "hybrid_rrf"):
            hits = self.suite.search(method, "đồ thị", filters={"chapter": 2}, top_k=3)
            self.assertEqual([hit["id"] for hit in hits], ["b"])
            self.assertEqual(hits[0]["metadata"]["extraction_quality"], "needs_review")
            quality_hits = self.suite.search(method, "đồ thị",
                                             filters={"extraction_quality": "needs_review"})
            self.assertEqual([hit["id"] for hit in quality_hits], ["b"])
            self.assertEqual(self.suite.search(method, "đồ thị", filters={"chapter": 99}), [])
        self.assertEqual(self.suite.tfidf("khôngcótừnày"), [])
        self.assertEqual(self.suite.tfidf("đồ thị", filters={"source_id": "unknown"}), [])

    def test_bad_request_and_dense_corpus_guard(self):
        with self.assertRaises(ValueError):
            self.suite.search("dense", "", top_k=3)
        with self.assertRaises(ValueError):
            self.suite.search("tfidf", "đồ thị", top_k=0)
        with self.assertRaises(ValueError):
            self.suite.search("hybrid_rrf", "đồ thị", rrf_k=0)
        self.backend.rows = [row("outside", "đồ thị", 1)]
        with self.assertRaisesRegex(RuntimeError, "outside approved V2"):
            self.suite.dense("đồ thị")

    def test_dev_evaluator_never_passes_gold_to_search(self):
        question = {"id": "d", "split": "dev", "question": "đồ thị", "answerable": True,
                    "expected_answer": "cây khung", "gold": [{"chunk_id": "a", "source_id": "doc",
                                                               "page": 1, "evidence": "cây khung"}]}
        metrics, traces = run_dev(self.suite, [question])
        self.assertEqual(len(traces), 3)
        self.assertEqual(metrics["answerable_count"], 1)
        self.assertEqual(metrics["strategies"]["tfidf"]["hit1"]["total"], 1)
        self.assertTrue(all(call[0] == "đồ thị" and call[1] == {} for call in self.backend.calls))
        self.assertTrue(all(trace["filters"] == {} for trace in traces))


class BenchmarkV2ShapeTests(unittest.TestCase):
    def test_benchmark_counts_and_gold_resolve_without_running_test_queries(self):
        rows, _ = approved_rows()
        by_id = {item["id"]: item for item in rows}
        manifest = json.loads((ROOT / "data/benchmark_v2_manifest.json").read_text(encoding="utf-8"))
        dev, _ = load_dev_benchmark(ROOT / "data/benchmark_v2_dev.json", rows)
        test = json.loads((ROOT / "data/benchmark_v2_test.json").read_text(encoding="utf-8-sig"))
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT / "data/benchmark_v2_dev.json").read_bytes()).hexdigest(),
                         manifest["dev"]["sha256"])
        self.assertEqual(hashlib.sha256((ROOT / "data/benchmark_v2_test.json").read_bytes()).hexdigest(),
                         manifest["test"]["sha256"])
        self.assertEqual((len(dev), sum(q["answerable"] for q in dev)), (17, 15))
        self.assertEqual((len(test), sum(q["answerable"] for q in test)), (7, 5))
        self.assertFalse({q["id"] for q in dev} & {q["id"] for q in test})
        for question in test:
            self.assertEqual(question["split"], "test")
            self.assertNotIn("filter", question)
            if question["answerable"]:
                self.assertTrue(question["expected_answer"])
                for gold in question["gold"]:
                    item = by_id[gold["chunk_id"]]
                    self.assertEqual((item["source_id"], item["page"]),
                                     (gold["source_id"], gold["page"]))
                    self.assertTrue(evidence_in_text(gold["evidence"], item["text"]))
            else:
                self.assertEqual(question["expected_behavior"], "search_and_abstain")
                self.assertTrue(question["absence_check"])


@unittest.skipUnless(os.getenv("RUN_LIVE_V2_TESTS") == "1", "set RUN_LIVE_V2_TESTS=1 for pgvector test")
class LiveV2ConnectionTests(unittest.TestCase):
    def test_read_only_connection_ranking_filter_and_empty_result(self):
        suite, store, _, _ = live_suite()
        before = database_snapshot(store)
        self.assertEqual(before[STRATEGY],
                         {"count": 332, "min_dimensions": 384, "max_dimensions": 384})
        dense = suite.dense("định nghĩa mệnh đề", top_k=3)
        self.assertTrue(dense)
        self.assertEqual([hit["score"] for hit in dense],
                         sorted((hit["score"] for hit in dense), reverse=True))
        for method in ("dense", "tfidf", "hybrid_rrf"):
            filtered = suite.search(method, "quan hệ thứ tự", filters={"chapter": 3})
            self.assertTrue(filtered)
            self.assertTrue(all(hit["metadata"]["chapter"] == 3 for hit in filtered))
            review = suite.search(method, "đồ thị", filters={"extraction_quality": "needs_review"})
            self.assertTrue(review)
            self.assertTrue(all(hit["metadata"]["extraction_quality"] == "needs_review"
                                for hit in review))
            cited = suite.search(method, "bảng chân trị",
                                 filters={"document_id": "chuong-1-co-so-logic", "page": 16})
            self.assertEqual([hit["id"] for hit in cited], ["chuong-1-co-so-logic:p16:c1:v2"])
            self.assertEqual(suite.search(method, "quan hệ thứ tự", filters={"chapter": 99}), [])
        self.assertEqual(database_snapshot(store), before)


if __name__ == "__main__":
    unittest.main()
