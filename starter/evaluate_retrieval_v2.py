"""Compare three V2 retrievers on the development split only; never open test."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
from datetime import datetime, timezone
from typing import Any

from baseline import pack_context
from index_discrete_math_v2 import STRATEGY, database_snapshot, file_sha256
from retrieval_v2 import V2RetrievalSuite, live_suite

ROOT = Path(__file__).resolve().parents[1]
DEV_BENCHMARK = ROOT / "data" / "benchmark_v2_dev.json"
BENCHMARK_MANIFEST = ROOT / "data" / "benchmark_v2_manifest.json"
STRATEGIES = ("dense", "tfidf", "hybrid_rrf")
TOP_K = 3
CONTEXT_BUDGET_CHARS = 800
CANDIDATE_K = 20
RRF_K = 60


def evidence_in_text(evidence: str, text: str) -> bool:
    """Ignore PDF line wrapping while still requiring the exact word sequence."""
    return " ".join(evidence.split()) in " ".join(text.split())


def load_dev_benchmark(path: Path, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Validate only dev. The test split is a separate file and never opened here."""
    raw = path.read_bytes()
    questions = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(questions, list) or len(questions) < 17:
        raise ValueError("Day07 dev benchmark needs at least 17 questions")
    by_id = {row["id"]: row for row in rows}
    seen: set[str] = set()
    answerable = 0
    absent = 0
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("Benchmark question must be an object")
        query_id = question.get("id")
        query = question.get("question")
        if (not isinstance(query_id, str) or not query_id or query_id in seen
                or question.get("split") != "dev" or not isinstance(query, str) or not query.strip()):
            raise ValueError(f"Invalid or duplicate dev question: {query_id}")
        seen.add(query_id)
        if question.get("filter") not in (None, {}):
            raise ValueError("This controlled benchmark uses raw questions without filters")
        if question.get("answerable") is True:
            answerable += 1
            if not isinstance(question.get("expected_answer"), str) or not question["expected_answer"].strip():
                raise ValueError(f"Answerable question lacks expected answer: {query_id}")
            gold = question.get("gold")
            if not isinstance(gold, list) or not gold:
                raise ValueError(f"Answerable question lacks gold evidence: {query_id}")
            for evidence in gold:
                if not isinstance(evidence, dict):
                    raise ValueError(f"Malformed gold evidence: {query_id}")
                row = by_id.get(evidence.get("chunk_id"))
                if (row is None or row["source_id"] != evidence.get("source_id")
                        or row["page"] != evidence.get("page")
                        or not isinstance(evidence.get("evidence"), str)
                        or not evidence_in_text(evidence["evidence"], row["text"])):
                    raise ValueError(f"Gold evidence is absent from V2: {query_id}")
        elif question.get("answerable") is False:
            absent += 1
            if (question.get("gold") or question.get("expected_answer")
                    or question.get("expected_behavior") != "search_and_abstain"
                    or not question.get("absence_reason") or not question.get("absence_check")):
                raise ValueError(f"Missing-evidence question is malformed: {query_id}")
        else:
            raise ValueError(f"answerable must be boolean: {query_id}")
    if answerable < 15 or absent < 2:
        raise ValueError(f"Dev split is too small: {answerable} answerable, {absent} missing evidence")
    return questions, hashlib.sha256(raw).hexdigest()


def evidence_hit(hit: dict[str, Any], gold: list[dict[str, Any]]) -> bool:
    return any(hit["id"] == item["chunk_id"]
               and hit["source_id"] == item["source_id"]
               and hit["page"] == item["page"]
               and evidence_in_text(item["evidence"], hit["text"]) for item in gold)


def run_dev(suite: V2RetrievalSuite, questions: list[dict[str, Any]]) -> tuple[dict, list[dict]]:
    traces: list[dict[str, Any]] = []
    for question in questions:
        # Only the raw user question enters search. Gold/expected answer are used after retrieval.
        query = question["question"]
        for strategy in STRATEGIES:
            started = time.perf_counter()
            hits = suite.search(strategy, query, filters=None, top_k=TOP_K,
                                candidate_k=CANDIDATE_K, rrf_k=RRF_K)
            retrieval_ms = (time.perf_counter() - started) * 1000.0
            context_started = time.perf_counter()
            context, context_ids = pack_context(hits, budget=CONTEXT_BUDGET_CHARS)
            context_ms = (time.perf_counter() - context_started) * 1000.0
            answerable = question["answerable"]
            gold = question.get("gold", [])
            marked = [{**hit, "gold_evidence_hit": evidence_hit(hit, gold) if answerable else None}
                      for hit in hits]
            trace = {
                "query_id": question["id"], "split": "dev", "question": query,
                "answerable": answerable, "strategy": strategy, "filters": {},
                "top_k": TOP_K, "candidate_k": CANDIDATE_K if strategy == "hybrid_rrf" else None,
                "rrf_k": RRF_K if strategy == "hybrid_rrf" else None,
                "results": marked, "context": context, "context_ids": context_ids,
                "context_chars": len(context), "context_budget_chars": CONTEXT_BUDGET_CHARS,
                "retrieval_ms": retrieval_ms, "context_ms": context_ms,
                "hit1": bool(marked and marked[0]["gold_evidence_hit"]) if answerable else None,
                "evidence_hit3": any(hit["gold_evidence_hit"] for hit in marked) if answerable else None,
                "context_evidence": any(hit["gold_evidence_hit"] and hit["id"] in context_ids
                                        for hit in marked) if answerable else None,
            }
            traces.append(trace)
    metrics = {"split": "dev", "corpus_chunks": len(suite.rows),
               "top_k": TOP_K, "context_budget_chars": CONTEXT_BUDGET_CHARS,
               "context_budget_unit": "Unicode characters including citation header",
               "question_count": len(questions),
               "answerable_count": sum(q["answerable"] for q in questions),
               "missing_evidence_count": sum(not q["answerable"] for q in questions),
               "strategies": {}}
    denominator = metrics["answerable_count"]
    for strategy in STRATEGIES:
        subset = [trace for trace in traces if trace["strategy"] == strategy]
        answerable = [trace for trace in subset if trace["answerable"]]
        latencies = sorted(trace["retrieval_ms"] for trace in subset)
        hit1 = sum(trace["hit1"] for trace in answerable)
        hit3 = sum(trace["evidence_hit3"] for trace in answerable)
        context = sum(trace["context_evidence"] for trace in answerable)
        metrics["strategies"][strategy] = {
            "hit1": {"count": hit1, "total": denominator, "rate": hit1 / denominator},
            "evidence_hit3": {"count": hit3, "total": denominator, "rate": hit3 / denominator},
            "context_evidence_rate": {"count": context, "total": denominator,
                                      "rate": context / denominator},
            "returned_results": sum(len(trace["results"]) for trace in subset),
            "zero_result_queries": sum(not trace["results"] for trace in subset),
            "median_retrieval_ms": statistics.median(latencies),
            "p95_retrieval_ms": latencies[math.ceil(0.95 * len(latencies)) - 1],
            "mean_retrieval_ms": statistics.mean(latencies),
            "mean_context_chars": statistics.mean(trace["context_chars"] for trace in subset),
            "service_cost_usd": 0,
            "hardware_cost_usd": "not measured",
        }
    return metrics, traces


def main() -> None:
    parser = argparse.ArgumentParser(description="Dev-only retrieval comparison; no test option")
    parser.add_argument("--dev-benchmark", type=Path, default=DEV_BENCHMARK)
    parser.add_argument("--output", type=Path, help="New result directory; existing runs are never overwritten")
    args = parser.parse_args()
    suite, store, hashes, startup_seconds = live_suite()
    before = database_snapshot(store)
    questions, benchmark_sha256 = load_dev_benchmark(args.dev_benchmark, suite.rows)
    locked = json.loads(BENCHMARK_MANIFEST.read_text(encoding="utf-8-sig"))
    if (benchmark_sha256 != locked["dev"]["sha256"]
            or hashes["v2_sha256"] != locked["corpus_sha256"]):
        raise RuntimeError("Dev benchmark or approved corpus differs from the locked manifest")
    metrics, traces = run_dev(suite, questions)
    after = database_snapshot(store)
    if before != after:
        raise RuntimeError("Database strategy counts/dimensions changed during read-only evaluation")
    if hashes != {"v1_sha256": file_sha256(ROOT / "starter/data/indexed/discrete_math/chunks.json"),
                  "v2_sha256": file_sha256(ROOT / "starter/data/indexed/discrete_math/chunks_v2.json")}:
        raise RuntimeError("V1/V2 JSON changed during evaluation")
    result_dir = args.output or (ROOT / "starter/results/discrete_math_v2" /
                                ("dev-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")))
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "split": "dev", "benchmark_path": str(args.dev_benchmark.resolve()),
        "benchmark_sha256": benchmark_sha256, "corpus_hashes": hashes,
        "strategy": STRATEGY, "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "dimensions": 384, "database_before": before, "database_after": after,
        "startup_seconds_including_model_db_validation_tfidf": startup_seconds,
        "tfidf_build_seconds": suite.tfidf_build_seconds,
        "candidate_k": CANDIDATE_K, "rrf_k": RRF_K,
        "test_benchmark_opened": False, "corpus_reembedded": False,
    }
    result_dir.mkdir(parents=True, exist_ok=False)
    for name, data in (("metrics.json", metrics), ("traces.json", traces), ("run_manifest.json", manifest)):
        (result_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    print(json.dumps({"result_dir": str(result_dir), "metrics": metrics,
                      "benchmark_sha256": benchmark_sha256}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
