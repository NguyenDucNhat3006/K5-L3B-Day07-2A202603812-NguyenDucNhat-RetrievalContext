"""Offline A2 retrieval variants over the approved Discrete Math V2 rows.

No database, embedding model, benchmark labels, or external API is used by the
retrievers. Gold is read only by the evaluation layer after retrieval finishes.
"""
from __future__ import annotations

import json
import math
import re
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from baseline import TfidfIndex, tokenize
from context_engineering_v2 import pack_c0
from evaluate_retrieval_v2 import BENCHMARK_MANIFEST, DEV_BENCHMARK, evidence_hit, load_dev_benchmark
from index_discrete_math_v2 import file_sha256
from retrieval_v2 import approved_rows

ROOT = Path(__file__).resolve().parents[1]
FROZEN_R0 = ROOT / "starter/results/discrete_math_v2/dev-20261116T043019037173Z/traces.json"
FROZEN_R0_SHA256 = "33d0d4c73598230273cf9b27533b9bfea7d888f2747dceb8c377f41ec0f16022"
TOP_K = 3
CONTEXT_BUDGET = 800

# Generic Vietnamese/English vocabulary for this subject; contains no benchmark
# question, expected answer, gold location, source, page, or chunk identifier.
TERM_GROUPS: dict[str, tuple[str, ...]] = {
    "mệnh đề": ("proposition", "logic", "phát biểu", "chân trị"),
    "bảng chân trị": ("truth table", "chân trị", "mệnh đề", "logic"),
    "phép kéo theo": ("implication", "kéo theo", "điều kiện đủ", "điều kiện cần"),
    "tương đương logic": ("logical equivalence", "tương đương", "đồng nhất thức"),
    "lượng từ": ("quantifier", "vị từ", "predicate", "tồn tại", "mọi"),
    "quan hệ": ("relation", "quan hệ hai ngôi", "cặp có thứ tự"),
    "quan hệ tương đương": ("equivalence relation", "phản xạ", "đối xứng", "bắc cầu"),
    "quan hệ thứ tự": ("partial order", "thứ tự bộ phận", "phản đối xứng", "bắc cầu"),
    "đồ thị": ("graph", "đỉnh", "cạnh", "bậc"),
    "đường đi": ("path", "chu trình", "liên thông", "đồ thị"),
    "euler": ("Euler", "đường đi Euler", "chu trình Euler", "bậc đỉnh"),
    "hamilton": ("Hamilton", "chu trình Hamilton", "đường đi Hamilton"),
    "cây": ("tree", "cây khung", "đỉnh", "cạnh", "liên thông"),
    "ma trận": ("matrix", "ma trận kề", "ma trận liên thuộc"),
    "định nghĩa": ("definition", "được gọi là", "khi và chỉ khi"),
    "định lý": ("theorem", "định lý", "chứng minh"),
}


def expand_query(query: str) -> str:
    """Append generic subject terms only when their phrase occurs in the query."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    folded = " ".join(query.casefold().split())
    extras: list[str] = []
    for phrase, terms in TERM_GROUPS.items():
        if phrase in folded:
            extras.extend(terms)
    # Stable deduplication prevents repeated query terms inflating TF-IDF weights.
    seen = set(tokenize(query))
    additions = []
    for term in extras:
        normalized = " ".join(tokenize(term))
        if normalized and normalized not in seen:
            additions.append(term)
            seen.add(normalized)
    return query if not additions else query + " " + " ".join(additions)


class OfflineA2:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        if not rows or len({r.get("id") for r in rows}) != len(rows):
            raise ValueError("V2 corpus must contain unique chunks")
        self.rows = rows
        self.by_id = {r["id"]: r for r in rows}
        self.index = TfidfIndex(rows)

    def search(self, query: str, variant: str, top_k: int = TOP_K) -> list[dict[str, Any]]:
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        if variant not in ("R1", "R2"):
            raise ValueError(f"unknown A2 variant: {variant}")
        expanded = expand_query(query)
        if variant == "R1":
            candidates = self.index.search(expanded, top_k=top_k)
            return [self._ranked(hit, rank, "R1", expanded_query=expanded)
                    for rank, hit in enumerate(candidates, 1)]

        # R2 unions two lexical candidate lists, then reranks with weighted RRF.
        # Candidate expansion is generic and does not access gold labels.
        original = self.index.search(query, top_k=min(30, len(self.rows)))
        expanded_hits = self.index.search(expanded, top_k=min(30, len(self.rows)))
        ranks: dict[str, dict[str, int | float | None]] = defaultdict(
            lambda: {"original_rank": None, "expanded_rank": None, "score": 0.0})
        for list_name, hits, weight in (("original_rank", original, 1.0),
                                        ("expanded_rank", expanded_hits, 1.0)):
            for rank, hit in enumerate(hits, 1):
                entry = ranks[hit["id"]]
                entry[list_name] = rank
                entry["score"] = float(entry["score"]) + weight / (60 + rank)
        ids = sorted(ranks, key=lambda chunk_id: (
            -float(ranks[chunk_id]["score"]),
            min(r for r in (ranks[chunk_id]["original_rank"], ranks[chunk_id]["expanded_rank"])
                if r is not None), chunk_id))[:top_k]
        return [self._ranked(self.by_id[chunk_id], rank, "R2",
                             score=float(ranks[chunk_id]["score"]),
                             original_rank=ranks[chunk_id]["original_rank"],
                             expanded_rank=ranks[chunk_id]["expanded_rank"],
                             expanded_query=expanded)
                for rank, chunk_id in enumerate(ids, 1)]

    @staticmethod
    def _ranked(row: dict[str, Any], rank: int, variant: str, **extra: Any) -> dict[str, Any]:
        score = extra.pop("score", row.get("score", 0.0))
        if not math.isfinite(float(score)):
            raise ValueError("score must be finite")
        return {**row, "chunk_id": row["id"], "rank": rank, "score": float(score),
                "strategy": variant, **extra}


def load_frozen_r0(questions: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    raw = FROZEN_R0.read_bytes()
    if __import__("hashlib").sha256(raw).hexdigest() != FROZEN_R0_SHA256:
        raise RuntimeError("Frozen R0 traces changed; refusing to overwrite/replace baseline")
    traces = json.loads(raw.decode("utf-8-sig"))
    by_row = {r["id"]: r for r in rows}
    qids = {q["id"] for q in questions}
    tfidf: dict[str, dict[str, Any]] = {}
    for trace in traces:
        if trace.get("split") != "dev" or trace.get("strategy") != "tfidf":
            continue
        qid = trace.get("query_id")
        if qid not in qids or qid in tfidf or trace.get("question") != next(q["question"] for q in questions if q["id"] == qid):
            raise RuntimeError(f"Frozen R0 trace does not match dev benchmark: {qid}")
        hits = trace.get("results")
        if len(hits) != 3:
            raise RuntimeError(f"Frozen R0 expected Top-3 for {qid}")
        clean = []
        for rank, hit in enumerate(hits, 1):
            row = by_row.get(hit.get("id"))
            if row is None or hit.get("rank") != rank or any(hit.get(k) != row[k] for k in
                    ("text", "source_id", "source", "page", "metadata")):
                raise RuntimeError(f"Frozen R0 citation mismatch for {qid} rank {rank}")
            clean.append({**row, "score": hit["score"], "rank": rank,
                          "chunk_id": row["id"], "strategy": "R0"})
        tfidf[qid] = {"hits": clean, "retrieval_ms": trace["retrieval_ms"]}
    if set(tfidf) != qids:
        raise RuntimeError("Frozen R0 does not cover exactly the locked dev questions")
    return tfidf


def run_a2(rows: list[dict[str, Any]], questions: list[dict[str, Any]], r0: dict[str, list[dict[str, Any]]]):
    suite = OfflineA2(rows)
    traces: list[dict[str, Any]] = []
    for question in questions:
        # Retrieval sees only the question. Gold fields are inspected below.
        for variant in ("R0", "R1", "R2"):
            if variant == "R0":
                hits = r0[question["id"]]["hits"]
                retrieval_ms = r0[question["id"]]["retrieval_ms"]
            else:
                start = time.perf_counter()
                hits = suite.search(question["question"], variant)
                retrieval_ms = (time.perf_counter() - start) * 1000
            pack_start = time.perf_counter()
            context, context_ids = pack_c0(hits, CONTEXT_BUDGET)
            packing_ms = (time.perf_counter() - pack_start) * 1000
            gold = question.get("gold", []) if question["answerable"] else []
            marked = [{**hit, "gold_evidence_hit": evidence_hit(hit, gold) if gold else None}
                      for hit in hits]
            context_hit = any(hit["gold_evidence_hit"] and hit["id"] in context_ids
                              for hit in marked) if gold else None
            traces.append({
                "query_id": question["id"], "split": "dev", "question": question["question"],
                "answerable": question["answerable"], "variant": variant, "top_k": TOP_K,
                "expanded_query": (expand_query(question["question"]) if variant != "R0" else None),
                "results": marked, "context": context, "context_ids": context_ids,
                "context_chars": len(context), "context_budget_chars": CONTEXT_BUDGET,
                "retrieval_ms": retrieval_ms, "packing_ms": packing_ms,
                "hit1": bool(marked and marked[0]["gold_evidence_hit"]) if gold else None,
                "evidence_hit3": any(h["gold_evidence_hit"] for h in marked) if gold else None,
                "context_evidence": context_hit,
                "unanswerable_has_results": bool(marked) if not question["answerable"] else None,
                "extraction_review_ids": [h["id"] for h in hits
                                          if h["metadata"].get("extraction_quality") == "needs_review"],
            })
    answerable_count = sum(q["answerable"] for q in questions)
    metrics: dict[str, Any] = {"split": "dev", "question_count": len(questions),
        "answerable_count": answerable_count, "unanswerable_count": len(questions)-answerable_count,
        "corpus_chunks": len(rows), "top_k": TOP_K, "context_budget_chars": CONTEXT_BUDGET,
        "context_budget_unit": "Unicode characters including citation header", "variants": {}}
    for variant in ("R0", "R1", "R2"):
        subset = [t for t in traces if t["variant"] == variant]
        eligible = [t for t in subset if t["answerable"]]
        latencies = [t["retrieval_ms"] for t in subset]
        hit1 = sum(bool(t["hit1"]) for t in eligible)
        hit3 = sum(bool(t["evidence_hit3"]) for t in eligible)
        context_hits = sum(bool(t["context_evidence"]) for t in eligible)
        risks = sum(len(t["extraction_review_ids"]) for t in subset)
        metrics["variants"][variant] = {
            "hit_at_1": {"count": hit1, "total": answerable_count, "rate": hit1/answerable_count},
            "evidence_hit_at_3": {"count": hit3, "total": answerable_count, "rate": hit3/answerable_count},
            "context_evidence_rate": {"count": context_hits, "total": answerable_count,
                                      "rate": context_hits/answerable_count},
            "median_retrieval_ms": statistics.median(latencies),
            "mean_retrieval_ms": statistics.mean(latencies),
            "mean_packing_ms": statistics.mean(t["packing_ms"] for t in subset),
            "mean_context_chars": statistics.mean(t["context_chars"] for t in subset),
            "mean_chunks_in_context": statistics.mean(len(t["context_ids"]) for t in subset),
            "zero_result_questions": sum(not t["results"] for t in subset),
            "needs_review_hits": risks,
            "unanswerable_retrieval_nonempty": sum(bool(t["results"]) for t in subset if not t["answerable"]),
            "service_cost_usd": 0, "database_accessed": False, "embeddings_created": 0,
        }
    return metrics, traces


def main() -> None:
    rows, hashes = approved_rows()
    questions, dev_hash = load_dev_benchmark(DEV_BENCHMARK, rows)
    locked = json.loads(BENCHMARK_MANIFEST.read_text(encoding="utf-8-sig"))
    if dev_hash != locked["dev"]["sha256"] or hashes["v2_sha256"] != locked["corpus_sha256"]:
        raise RuntimeError("Dev benchmark or approved V2 corpus differs from locked manifest")
    if len(rows) != 332 or len(questions) != 17:
        raise RuntimeError("A2 requires the approved 332 chunk corpus and exact 17-question dev split")
    r0 = load_frozen_r0(questions, rows)
    metrics, traces = run_a2(rows, questions, r0)
    output = ROOT / "starter/results/discrete_math_v2" / (
        "retrieval-a2-dev-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "split": "dev",
        "benchmark_dev_sha256": dev_hash, "corpus_hashes": hashes,
        "frozen_r0_trace_sha256": FROZEN_R0_SHA256, "variants": {
            "R0": "Frozen original TF-IDF rankings; C0 repacked consistently to 800 Unicode chars",
            "R1": "TF-IDF query expansion using generic Vietnamese/English Discrete Math vocabulary",
            "R2": "Union of original and expanded TF-IDF Top-30, reranked with RRF (k=60)"},
        "top_k": TOP_K, "context_packer": "C0", "context_budget_chars": CONTEXT_BUDGET,
        "gold_used_for_query_or_filter": False, "test_benchmark_opened": False,
        "database_accessed": False, "database_written": False, "embeddings_created": 0,
        "llm_api_calls": 0, "R0_latency_source": "frozen original TF-IDF retrieval_ms",
        "R1_R2_latency_source": "measured locally during offline run; excludes index construction"}
    for name, obj in (("metrics.json", metrics), ("traces.json", traces), ("run_manifest.json", manifest)):
        (output / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
