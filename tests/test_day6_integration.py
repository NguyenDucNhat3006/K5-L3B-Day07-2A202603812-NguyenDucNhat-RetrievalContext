import unittest
from types import SimpleNamespace

from starter.day6_integration import chapter_from_filename, chunk_id, slugify, to_day7_chunk


class Day6IntegrationTests(unittest.TestCase):
    def test_slug_preserves_vietnamese_d_as_d(self):
        self.assertEqual(slugify("Chuong 4. Đai số Boole"), "chuong-4-dai-so-boole")

    def test_chapter_only_comes_from_filename(self):
        self.assertEqual(chapter_from_filename("bai tap chuong 5.pdf"), 5)
        self.assertIsNone(chapter_from_filename("notes.pdf"))

    def test_chunk_id_matches_day7_contract(self):
        self.assertEqual(chunk_id("policy-1", 1, 1), "policy-1:p1:c1")
        for values in (("", 1, 1), ("doc", 0, 1), ("doc", 1, 0)):
            with self.assertRaises(ValueError):
                chunk_id(*values)

    def test_export_uses_the_day7_chunk_schema(self):
        chunk = SimpleNamespace(
            chunk_id="internal-id",
            page=1,
            text="Yêu cầu hoàn tiền được xử lý trong 7 ngày làm việc.",
            metadata={"version": "2025"},
        )
        row = to_day7_chunk(chunk, "policy-1", "example://policy-1", 1)
        self.assertEqual(set(row), {"id", "text", "source_id", "source", "page", "metadata"})
        self.assertEqual(row["id"], "policy-1:p1:c1")
        self.assertEqual(row["metadata"], {"version": "2025"})


if __name__ == "__main__":
    unittest.main()
