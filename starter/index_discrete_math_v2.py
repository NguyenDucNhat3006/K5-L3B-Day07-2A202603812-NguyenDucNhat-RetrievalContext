"""Index the approved Day 7 v2 JSON in Day 6 pgvector and smoke-test retrieval.

This command reads v1/v2 JSON without changing either file. It never reads the
benchmark or runs evaluation. The v2 strategy is separate from Day 6 A/B.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Any

from day6_integration import Day6DenseRetriever, chapter_from_filename, slugify
from index_discrete_math import EXPECTED_MODEL, discover_day6_root, load_day6_modules

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "discrete_math" / "raw"
DATA = ROOT / "starter" / "data" / "indexed" / "discrete_math"
V1 = DATA / "chunks.json"
V2 = DATA / "chunks_v2.json"
PAYLOAD = DATA / "chunks_v2_index_ready.json"
INFO = DATA / "index_info_v2.json"
TRACES = DATA / "smoke_traces_v2.json"
REPORT = ROOT / "report" / "individual" / "v2_index_smoke.md"
STRATEGY = "D07_discrete_math_v2"
APPROVED_V1_SHA256 = "7561e3a39e06b919b5872e2e3f9083c6ef2d67c739c5329464d6d7090aba515d"
APPROVED_V2_SHA256 = "979a0baaf2f34735592bde1aeaf2bdb29b5a8f336f3f0bcb3fee699056f57990"
TARGET_CHARS = 500
HARD_LIMIT_CHARS = 620
EXPECTED_DIMENSIONS = 384


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_inputs() -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Pin the reviewed JSON and verify every physical citation target."""
    hashes = {"v1_sha256": file_sha256(V1), "v2_sha256": file_sha256(V2)}
    if hashes != {"v1_sha256": APPROVED_V1_SHA256, "v2_sha256": APPROVED_V2_SHA256}:
        raise RuntimeError("The reviewed V1/V2 JSON changed; inspect it before indexing")
    rows = json.loads(V2.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or len(rows) != 332:
        raise ValueError("Expected the approved 332-row V2 corpus")
    expected_keys = {"id", "text", "source_id", "source", "page", "metadata"}
    ids, page_counts = set(), {}
    from pypdf import PdfReader

    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_keys:
            raise ValueError("V2 row does not match the Day 7 chunk schema")
        chunk_id, source_id, source, page, text, metadata = (row[key] for key in
            ("id", "source_id", "source", "page", "text", "metadata"))
        if (not all(isinstance(value, str) and value.strip() for value in (chunk_id, source_id, source, text))
                or not isinstance(page, int) or isinstance(page, bool) or page < 1
                or not isinstance(metadata, dict) or chunk_id in ids):
            raise ValueError(f"Invalid V2 ID, source, page, text or metadata: {chunk_id!r}")
        ids.add(chunk_id)
        match = re.fullmatch(re.escape(source_id) + r":p(\d+):c(\d+):v2", chunk_id)
        if not match or int(match.group(1)) != page:
            raise ValueError(f"Chunk ID/page mismatch: {chunk_id}")
        path = (ROOT / source).resolve()
        if path.parent != RAW.resolve() or not path.is_file() or source_id != slugify(path.stem):
            raise ValueError(f"Missing or mismatched PDF source for {chunk_id}")
        if path not in page_counts:
            page_counts[path] = len(PdfReader(path, strict=False).pages)
        if page > page_counts[path] or metadata.get("chapter") != chapter_from_filename(path.stem):
            raise ValueError(f"Physical page or chapter mismatch: {chunk_id}")
        if (metadata.get("subject") != "discrete_math"
                or metadata.get("extraction_quality") not in {"ok", "needs_review"}
                or not isinstance(metadata.get("quality_reasons"), list)):
            raise ValueError(f"Missing review metadata: {chunk_id}")
        if len(text) > HARD_LIMIT_CHARS or "\ufffd" in text:
            raise ValueError(f"Chunk exceeds V2 hard limit or contains replacement text: {chunk_id}")
    long_rows = [row for row in rows if len(row["text"]) > TARGET_CHARS]
    if len(long_rows) != 22:
        raise ValueError(f"Expected 22 reviewed chunks over 500 chars; found {len(long_rows)}")
    return rows, hashes


def index_ready_rows(rows: list[dict[str, Any]], v2_sha256: str) -> list[dict[str, Any]]:
    """Add the explicit chunking policy to metadata; preserve ID/text/source/page."""
    ready = []
    for row in rows:
        reasons = row["metadata"]["quality_reasons"]
        metadata = {
            **row["metadata"],
            "chunk_target_chars": TARGET_CHARS,
            "chunk_hard_limit_chars": HARD_LIMIT_CHARS,
            "semantic_over_target": len(row["text"]) > TARGET_CHARS,
            "semantic_unit_split": "long_semantic_unit_split" in reasons,
            "approved_v2_sha256": v2_sha256,
        }
        ready.append({**row, "metadata": metadata})
    if any((a["id"], a["text"], a["source_id"], a["source"], a["page"]) !=
           (b["id"], b["text"], b["source_id"], b["source"], b["page"])
           for a, b in zip(rows, ready)):
        raise RuntimeError("Index payload changed a citation field or evidence text")
    return ready


def database_snapshot(store) -> dict[str, dict[str, int | None]]:
    """Read strategy counts and actual vector dimensions without exposing DSN."""
    with store._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT strategy, COUNT(*), MIN(vector_dims(embedding)), MAX(vector_dims(embedding)) "
                "FROM chunks GROUP BY strategy ORDER BY strategy"
            )
            records = cursor.fetchall()
    return {strategy: {"count": int(count), "min_dimensions": low, "max_dimensions": high}
            for strategy, count, low, high in records}


def stored_rows(store) -> list[tuple]:
    with store._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT chunk_id, document_id, source, page, text, metadata, vector_dims(embedding) "
                "FROM chunks WHERE strategy = %s ORDER BY chunk_id", (STRATEGY,)
            )
            return cursor.fetchall()


def verify_stored(rows: list[dict[str, Any]], actual: list[tuple]) -> None:
    expected = {row["id"]: row for row in rows}
    if len(actual) != len(expected):
        raise RuntimeError(f"V2 DB count mismatch: expected {len(expected)}, found {len(actual)}")
    for chunk_id, document_id, source, page, text, metadata, dimensions in actual:
        row = expected.get(chunk_id)
        if (row is None or (document_id, source, page, text, metadata, dimensions) !=
                (row["source_id"], row["source"], row["page"], row["text"], row["metadata"], EXPECTED_DIMENSIONS)):
            raise RuntimeError(f"Stored ID/source/page/text/metadata/vector dimension mismatch: {chunk_id}")


def smoke_queries(embedder, store) -> list[dict[str, Any]]:
    """Use illustrative Vietnamese questions; no benchmark file is opened."""
    retriever = Day6DenseRetriever(embedder, store, STRATEGY)
    cases = [
        ("Bảng chân trị của E(p,q,r) ở phần biểu thức logic", None),
        ("Quan hệ từ A đến B biểu diễn bằng ma trận như thế nào?", {"chapter": 3}),
        ("Phép duyệt tiền tự trên cây có gốc", {"subject": "discrete_math"}),
        ("Bảng chân trị của E(p,q,r)", {"document_id": "chuong-1-co-so-logic", "page": 16}),
        ("Ví dụ về đồ thị và cây khung", {"extraction_quality": "needs_review"}),
    ]
    traces = []
    for question, filters in cases:
        hits = retriever.search(question, filters=filters, top_k=3)
        if not hits:
            raise RuntimeError(f"Smoke retrieval returned no results: {question}")
        if any(not math.isfinite(hit["score"]) for hit in hits):
            raise RuntimeError("Non-finite similarity score in smoke retrieval")
        if [hit["score"] for hit in hits] != sorted((hit["score"] for hit in hits), reverse=True):
            raise RuntimeError("Smoke results are not ranked by score")
        for hit in hits:
            metadata = hit["metadata"]
            if not (hit["source_id"] and hit["source"] and hit["page"] >= 1
                    and metadata.get("subject") == "discrete_math"):
                raise RuntimeError("Smoke hit lost citation metadata")
            for key, value in (filters or {}).items():
                actual = {"document_id": hit["source_id"], "page": hit["page"], "source": hit["source"]}.get(key, metadata.get(key))
                if actual != value:
                    raise RuntimeError(f"SQL metadata filter failed: {key}={value!r}")
        traces.append({"question": question, "filters": filters or {}, "top_k": 3,
                       "results": [{"rank": rank, "id": hit["id"], "score": hit["score"],
                                    "source_id": hit["source_id"], "source": hit["source"],
                                    "page": hit["page"],
                                    "extraction_quality": hit["metadata"].get("extraction_quality")}
                                   for rank, hit in enumerate(hits, start=1)]})
    if retriever.search("kiểm tra filter rỗng", filters={"chapter": 99}, top_k=3):
        raise RuntimeError("A non-existent chapter returned V2 rows")
    return traces


def report_text(rows: list[dict[str, Any]], hashes: dict[str, str], before: dict,
                after: dict, seconds: float, traces: list[dict[str, Any]], reused: bool) -> str:
    long_rows = [row for row in rows if len(row["text"]) > TARGET_CHARS]
    split_long = [row for row in long_rows if row["metadata"]["semantic_unit_split"]]
    review = [row for row in rows if row["metadata"]["extraction_quality"] == "needs_review"]
    issue_groups = {
        "Bảng": {"table_columns_unreliable", "table_not_verified"},
        "Ma trận": {"matrix_requires_visual_check"},
        "Hình/đồ thị": {"diagram_requires_visual_check", "graph_exercise_requires_visual_check",
                        "logic_gate_diagram_requires_visual_check", "tree_diagram_requires_visual_check"},
        "Công thức/font": {"unmapped_formula_symbol", "math_layout_requires_visual_check"},
    }
    lines = [
        "# Kiểm tra index corpus Cấu trúc rời rạc V2",
        "",
        "V2 được dùng làm corpus thử nghiệm theo quyết định của người dùng. Báo cáo này chỉ ghi indexing và smoke retrieval, không ghi điểm benchmark.",
        "",
        "## Nguồn và chính sách chunk",
        "",
        f"- V1: `{hashes['v1_sha256']}`; V2 đã duyệt: `{hashes['v2_sha256']}` (SHA-256). Hai JSON nguồn được giữ nguyên byte.",
        f"- V2 có **{len(rows)}** chunk; **{len(long_rows)}** chunk dài hơn {TARGET_CHARS} ký tự, dài nhất {max(len(row['text']) for row in rows)}. Giới hạn mục tiêu là {TARGET_CHARS}, giới hạn cứng là {HARD_LIMIT_CHARS}; mọi chunk đều trong giới hạn cứng.",
        f"- **{len(long_rows) - len(split_long)}** chunk >500 giữ trọn đơn vị semantic; **{len(split_long)}** chunk >500 là phần của đơn vị dài hơn, có cờ `long_semantic_unit_split`. Không diễn giải hai chunk này là đơn vị nguyên vẹn.",
        "- Metadata của payload/DB có `chunk_target_chars`, `chunk_hard_limit_chars`, `semantic_over_target`, `semantic_unit_split`, `approved_v2_sha256`. Text, ID, source_id, source và page trùng V2 đã duyệt.",
        f"- `needs_review`: **{len(review)}/{len(rows)}** chunk; các cờ phản ánh rủi ro thiếu evidence và có thể chồng lấp.",
        "",
        "| Nhóm cần kiểm tra | Số chunk | Tất cả có needs_review? |",
        "|---|---:|---|",
    ]
    for label, reasons in issue_groups.items():
        subset = [row for row in rows if reasons.intersection(row["metadata"].get("quality_reasons", []))]
        lines.append(f"| {label} | {len(subset)} | {'có' if all(row['metadata']['extraction_quality'] == 'needs_review' for row in subset) else 'KHÔNG'} |")
    lines.extend([
        "",
        "Bảng chân trị có cấu trúc được giữ từ PDF khi trích xuất đáng tin cậy; bảng lệch cột, ma trận và hình chưa đọc đủ vẫn cần đối chiếu trang nguồn. Không bổ sung dữ liệu suy đoán từ hình.",
        "",
        "### 22 chunk vượt mục tiêu 500 ký tự",
        "",
        "| ID | Ký tự | Chính sách | extraction_quality |",
        "|---|---:|---|---|",
    ])
    for row in long_rows:
        policy = "đã tách từ đơn vị dài" if row["metadata"]["semantic_unit_split"] else "giữ đơn vị semantic"
        lines.append(f"| `{row['id']}` | {len(row['text'])} | {policy} | {row['metadata']['extraction_quality']} |")
    lines.extend([
        "",
        "## PostgreSQL + pgvector",
        "",
        f"- Strategy riêng: `{STRATEGY}`. Model: `{EXPECTED_MODEL}`; chiều vector: **{EXPECTED_DIMENSIONS}**.",
        f"- Trước indexing: V2 **{before.get(STRATEGY, {}).get('count', 0)}** hàng. Sau indexing: V2 **{after.get(STRATEGY, {}).get('count', 0)}** hàng. {'Đã tái sử dụng index V2 giống hệt, không re-embed.' if reused else f'Thời gian embedding: {seconds:.3f} giây.'}",
        f"- A_fixed **{before.get('A_fixed', {}).get('count', 0)} → {after.get('A_fixed', {}).get('count', 0)}**; B_paragraph **{before.get('B_paragraph', {}).get('count', 0)} → {after.get('B_paragraph', {}).get('count', 0)}**.",
        "- Đã đối chiếu toàn bộ ID, document_id, source, page, text, metadata và `vector_dims(embedding)` giữa JSON index-ready và các hàng DB của strategy V2.",
        "- Store Day06 dùng khóa `(strategy, chunk_id)`; câu `DELETE`/`UPSERT` đều giới hạn theo strategy. Vì vậy thao tác V2 không chạm các hàng A/B.",
        "",
        "## Smoke retrieval (câu minh họa, ngoài benchmark test)",
        "",
        "Các truy vấn dùng model Day06 thật và SQL pgvector; filter `chapter`, `subject`, `extraction_quality` chạy qua JSONB containment, còn `document_id/page` là điều kiện cột SQL. Không chấm đúng/sai hoặc grounding từ kết quả này.",
        "",
    ])
    for number, trace in enumerate(traces, start=1):
        lines.extend([f"### {number}. {trace['question']}", "",
                      f"Filter: `{json.dumps(trace['filters'], ensure_ascii=False)}`", "",
                      "| Rank | Chunk ID | Score | source_id | page | quality |",
                      "|---:|---|---:|---|---:|---|"])
        for hit in trace["results"]:
            lines.append(f"| {hit['rank']} | `{hit['id']}` | {hit['score']:.4f} | `{hit['source_id']}` | {hit['page']} | {hit['extraction_quality']} |")
        lines.append("")
    lines.extend([
        "## Giới hạn và bước tiếp theo",
        "",
        "- Smoke test xác nhận truy vấn, thứ hạng, citation và filter, chưa chứng minh câu trả lời đúng hoặc evidence đủ. Chunk `needs_review` cần người đối chiếu PDF trước khi dùng để đánh giá grounding.",
        "- Đã chạy Dense smoke; chưa chạy benchmark test hoặc xây/chấm bộ so sánh Dense, TF-IDF, Hybrid trên câu hỏi Lab07.",
        "- Quyền chia sẻ PDF và các trích đoạn trong báo cáo chưa được xác minh; cần kiểm tra trước khi công bố.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    rows, hashes = checked_inputs()
    ready = index_ready_rows(rows, hashes["v2_sha256"])
    DATA.mkdir(parents=True, exist_ok=True)
    PAYLOAD.write_text(json.dumps(ready, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    day6_root = discover_day6_root()
    _, _, MyEmbedder, PgVectorStore = load_day6_modules(day6_root)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL missing from Day06 starter/.env")
    model_name = os.getenv("EMBEDDING_MODEL") or EXPECTED_MODEL
    if model_name != EXPECTED_MODEL:
        raise ValueError(f"The Day06 embedding model differs from the approved V2 model: {model_name}")
    embedder = MyEmbedder(model_name)
    if embedder.dimensions != EXPECTED_DIMENSIONS:
        raise ValueError(f"Expected {EXPECTED_DIMENSIONS} dimensions; got {embedder.dimensions}")
    store = PgVectorStore(database_url, embedder.dimensions)
    before = database_snapshot(store)
    for name in ("A_fixed", "B_paragraph"):
        item = before.get(name)
        if not item or item["count"] <= 0 or item["min_dimensions"] != EXPECTED_DIMENSIONS or item["max_dimensions"] != EXPECTED_DIMENSIONS:
            raise RuntimeError(f"Day06 {name} index is missing or incompatible")
    from src.models import Chunk
    chunks = [Chunk(chunk_id=row["id"], document_id=row["source_id"], source=row["source"],
                    page=row["page"], text=row["text"], metadata=row["metadata"]) for row in ready]
    existing = stored_rows(store)
    reused = bool(existing)
    embedding_seconds = 0.0
    if existing:
        verify_stored(ready, existing)  # Never overwrite an existing different experiment.
    else:
        started = time.perf_counter()
        vectors = embedder.embed_documents([chunk.text for chunk in chunks])
        embedding_seconds = time.perf_counter() - started
        if len(vectors) != len(chunks) or any(len(vector) != EXPECTED_DIMENSIONS for vector in vectors):
            raise RuntimeError("Embedding count or dimensions do not match approved V2")
        store.upsert(STRATEGY, chunks, vectors, document_ids=sorted({chunk.document_id for chunk in chunks}))
    verify_stored(ready, stored_rows(store))
    after = database_snapshot(store)
    if after[STRATEGY]["count"] != len(ready) or any(after.get(name) != record for name, record in before.items() if name != STRATEGY):
        raise RuntimeError("V2 count mismatch or an existing strategy changed")
    traces = smoke_queries(embedder, store)
    if {"v1_sha256": file_sha256(V1), "v2_sha256": file_sha256(V2)} != hashes:
        raise RuntimeError("V1 or V2 JSON changed during indexing")
    info = {"strategy": STRATEGY, "model": model_name, "dimensions": embedder.dimensions,
            "input_hashes": hashes, "counts_before": before, "counts_after": after,
            "chunk_count": len(ready), "over_500": sum(len(row["text"]) > TARGET_CHARS for row in ready),
            "target_chars": TARGET_CHARS, "hard_limit_chars": HARD_LIMIT_CHARS,
            "embedding_seconds": round(embedding_seconds, 3), "reused_existing_index": reused,
            "smoke_queries": len(traces)}
    # Keep the first successful experiment's timing and traces on repeated runs.
    outputs = (
        (INFO, json.dumps(info, ensure_ascii=False, indent=2) + "\n"),
        (TRACES, json.dumps(traces, ensure_ascii=False, indent=2) + "\n"),
        (REPORT, report_text(ready, hashes, before, after, embedding_seconds, traces, reused)),
    )
    for path, content in outputs:
        if reused and path.exists():
            continue
        path.write_text(content, encoding="utf-8")
    print(json.dumps({"strategy": STRATEGY, "chunks": len(ready), "dimensions": embedder.dimensions,
                      "counts_before": before, "counts_after": after, "embedding_seconds": round(embedding_seconds, 3),
                      "reused_existing_index": reused, "smoke_queries": len(traces),
                      "report": str(REPORT)}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
