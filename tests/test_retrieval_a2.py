"""Unit coverage for offline A2 retrieval; no database or API access."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))

from retrieval_a2 import OfflineA2, expand_query


def chunk(chunk_id, text, page=1, quality="ok"):
    return {"id": chunk_id, "text": text, "source_id": "doc-1", "source": "doc-1.pdf",
            "page": page, "metadata": {"subject": "discrete_math", "chapter": 1,
                                       "content_type": "definition",
                                       "extraction_quality": quality}}


class RetrievalA2Tests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            chunk("c1", "Bảng chân trị của mệnh đề logic gồm các giá trị đúng sai."),
            chunk("c2", "Đồ thị gồm tập đỉnh và tập cạnh; bậc của đỉnh." , 2, "needs_review"),
            chunk("c3", "Quan hệ tương đương có tính phản xạ đối xứng bắc cầu.", 3),
            chunk("c4", "Cây là đồ thị liên thông không có chu trình.", 4),
        ]
        self.retriever = OfflineA2(self.rows)

    def test_expansion_is_generic_and_query_driven(self):
        expanded = expand_query("Giải thích bảng chân trị")
        self.assertIn("truth table", expanded)
        self.assertNotIn("c1", expanded)
        self.assertEqual(expand_query("khái niệm chưa có trong từ điển"),
                         "khái niệm chưa có trong từ điển")

    def test_r1_r2_top3_metadata_and_review_flags(self):
        for variant in ("R1", "R2"):
            hits = self.retriever.search("đồ thị và bậc đỉnh", variant, top_k=3)
            self.assertLessEqual(len(hits), 3)
            self.assertEqual([h["rank"] for h in hits], list(range(1, len(hits) + 1)))
            for hit in hits:
                self.assertEqual(hit["source"], "doc-1.pdf")
                self.assertEqual(hit["chunk_id"], hit["id"])
                self.assertIn(hit["metadata"]["extraction_quality"], ("ok", "needs_review"))
        r2 = self.retriever.search("đồ thị và bậc đỉnh", "R2", top_k=3)
        self.assertEqual(r2[0]["id"], "c2")
        self.assertEqual(r2[0]["metadata"]["extraction_quality"], "needs_review")

    def test_empty_query_bad_variant_and_top_k_rejected(self):
        with self.assertRaises(ValueError):
            expand_query("  ")
        with self.assertRaises(ValueError):
            self.retriever.search("đồ thị", "R3")
        with self.assertRaises(ValueError):
            self.retriever.search("đồ thị", "R1", top_k=0)

    def test_no_overlap_returns_empty_without_fabricating_evidence(self):
        self.assertEqual(self.retriever.search("zxyqv unknown-token", "R1"), [])
        self.assertEqual(self.retriever.search("zxyqv unknown-token", "R2"), [])


if __name__ == "__main__":
    unittest.main()
