"""Dev-only context packing over the frozen TF-IDF Top-3 retrieval traces.

No retrieval, corpus embedding or database access occurs here. Pack functions see
only the question and retrieved chunks; gold is used only after packing for metrics.
"""

from __future__ import annotations

import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import statistics
import time
from datetime import datetime, timezone
from typing import Any

from evaluate_retrieval_v2 import evidence_hit, load_dev_benchmark
from retrieval_v2 import approved_rows

ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_DIR = ROOT / "starter/results/discrete_math_v2/dev-20261116T043019037173Z"
RETRIEVAL_TRACES = RETRIEVAL_DIR / "traces.json"
RETRIEVAL_TRACES_SHA256 = "33d0d4c73598230273cf9b27533b9bfea7d888f2747dceb8c377f41ec0f16022"
DEV_BENCHMARK = ROOT / "data/benchmark_v2_dev.json"
BENCHMARK_MANIFEST = ROOT / "data/benchmark_v2_manifest.json"
BUDGET_CHARS = 800
TOKENIZER_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CONFIGS = ("C0", "C1")

VISUAL_OR_MATH_FLAGS = {
    "diagram_requires_visual_check", "graph_exercise_requires_visual_check",
    "tree_diagram_requires_visual_check", "logic_gate_diagram_requires_visual_check",
    "matrix_requires_visual_check", "math_layout_requires_visual_check",
    "unmapped_formula_symbol", "table_not_verified",
}


def citation_block(hit: dict[str, Any]) -> str:
    """Keep the complete semantic chunk and every citation field in the prompt."""
    for key in ("id", "text", "source", "page", "metadata"):
        if key not in hit:
            raise ValueError(f"retrieval hit lacks {key}")
    quality = hit["metadata"].get("extraction_quality")
    if quality not in ("ok", "needs_review"):
        raise ValueError("retrieval hit lacks extraction_quality")
    if not isinstance(hit["page"], int) or hit["page"] < 1:
        raise ValueError("retrieval hit has invalid page")
    return (f"[chunk_id={hit['id']} | source={hit['source']} | page={hit['page']} "
            f"| extraction_quality={quality}]\n{hit['text']}")


def assemble(hits: list[dict[str, Any]], budget_chars: int) -> tuple[str, list[str]]:
    if not isinstance(budget_chars, int) or budget_chars < 1:
        raise ValueError("budget_chars must be positive")
    ordered = sorted(hits, key=lambda hit: hit["rank"])
    context = "\n\n".join(citation_block(hit) for hit in ordered)
    if len(context) > budget_chars:
        raise ValueError("complete cited chunks exceed character budget")
    return context, [hit["id"] for hit in ordered]


def pack_c0(hits: list[dict[str, Any]], budget_chars: int = BUDGET_CHARS) -> tuple[str, list[str]]:
    """Original Top-3 order, greedily include each whole chunk if it fits."""
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hit in hits:
        if hit["id"] in seen:
            continue
        seen.add(hit["id"])
        trial = selected + [hit]
        if len("\n\n".join(citation_block(item) for item in trial)) <= budget_chars:
            selected = trial
    return assemble(selected, budget_chars)


def review_risk(hit: dict[str, Any]) -> str:
    """Describe ingestion risk; never infer missing diagram/table contents."""
    metadata = hit["metadata"]
    if metadata["extraction_quality"] == "ok":
        return "ok"
    reasons = set(metadata.get("quality_reasons", []))
    return "visual_or_math_review" if reasons & VISUAL_OR_MATH_FLAGS else "text_review"


def _utility(query: str, hit: dict[str, Any]) -> float:
    """Use retrieval rank, structure and extraction flags, never benchmark gold."""
    rank = hit["rank"]
    content_type = hit["metadata"].get("content_type")
    score = 1.4 - 0.3 * (rank - 1)
    if content_type in ("definition", "theorem", "truth_table"):
        score += 0.35
    elif content_type == "example":
        score += 0.15
    query_folded = query.casefold()
    cues = (("định nghĩa", "definition"), ("định lý", "theorem"),
            ("bảng chân trị", "truth_table"), ("ví dụ", "example"))
    if any(cue in query_folded and content_type == kind for cue, kind in cues):
        score += 0.45
    risk = review_risk(hit)
    if risk == "ok":
        score += 0.25
    elif risk == "visual_or_math_review":
        score -= 0.35
    if hit["metadata"].get("semantic_unit_split"):
        score -= 0.25
    return score


def pack_c1(query: str, hits: list[dict[str, Any]],
            budget_chars: int = BUDGET_CHARS) -> tuple[str, list[str]]:
    """Choose whole cited chunks by a small deterministic knapsack over Top-3."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be non-empty")
    if len(hits) > 3:
        raise ValueError("C1 expects frozen Top-3 candidates")
    best: tuple[float, int, int, int, str] | None = None
    selected: list[dict[str, Any]] = []
    for size in range(1, len(hits) + 1):
        for subset in combinations(hits, size):
            ordered = sorted(subset, key=lambda hit: hit["rank"])
            context = "\n\n".join(citation_block(hit) for hit in ordered)
            if len(context) > budget_chars:
                continue
            utility = sum(_utility(query, hit) for hit in ordered)
            key = (utility, len(ordered), -len(context),
                   -sum(hit["rank"] for hit in ordered),
                   "|".join(hit["id"] for hit in ordered))
            if best is None or key > best:
                best, selected = key, ordered
    return assemble(selected, budget_chars)


def frozen_tfidf_traces(questions: list[dict[str, Any]],
                        rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    raw = RETRIEVAL_TRACES.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != RETRIEVAL_TRACES_SHA256:
        raise RuntimeError("Frozen TF-IDF retrieval traces changed")
    all_traces = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(all_traces, list) or len(all_traces) != 51:
        raise ValueError("Expected the original 17 x 3 dev retrieval traces")
    if any(trace.get("split") != "dev" for trace in all_traces):
        raise ValueError("Non-dev retrieval trace found")
    tfidf = [trace for trace in all_traces if trace.get("strategy") == "tfidf"]
    if len(tfidf) != len(questions):
        raise ValueError("Expected one TF-IDF trace for each dev question")
    by_id = {row["id"]: row for row in rows}
    by_question = {question["id"]: question for question in questions}
    seen: set[str] = set()
    for trace in tfidf:
        query_id = trace.get("query_id")
        question = by_question.get(query_id)
        if (question is None or query_id in seen or trace.get("question") != question["question"]
                or trace.get("answerable") is not question["answerable"]
                or trace.get("filters") != {}):
            raise ValueError(f"TF-IDF trace does not match locked dev question: {query_id}")
        seen.add(query_id)
        hits = trace.get("results")
        if not isinstance(hits, list) or len(hits) != 3:
            raise ValueError(f"Expected frozen TF-IDF Top-3: {query_id}")
        for rank, hit in enumerate(hits, start=1):
            row = by_id.get(hit.get("id"))
            if (row is None or hit.get("rank") != rank or hit.get("chunk_id") != row["id"]
                    or any(hit.get(key) != row[key] for key in
                           ("text", "source_id", "source", "page", "metadata"))
                    or not isinstance(hit.get("score"), (int, float))
                    or not math.isfinite(hit["score"])):
                raise ValueError(f"TF-IDF hit/citation differs from V2: {query_id} rank {rank}")
    return sorted(tfidf, key=lambda trace: trace["query_id"]), digest


def run_contexts(questions: list[dict[str, Any]], tfidf: list[dict[str, Any]],
                 tokenizer: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_question = {question["id"]: question for question in questions}
    traces: list[dict[str, Any]] = []
    for retrieval in tfidf:
        question = by_question[retrieval["query_id"]]
        hits = retrieval["results"]
        for config in CONFIGS:
            start = time.perf_counter()
            context, ids = (pack_c0(hits) if config == "C0"
                            else pack_c1(question["question"], hits))
            packing_ms = (time.perf_counter() - start) * 1000.0
            tokens = len(tokenizer.encode(context, add_special_tokens=False,
                                          truncation=False))
            selected = [hit for hit in hits if hit["id"] in ids]
            gold = question.get("gold", [])
            has_evidence = (any(evidence_hit(hit, gold) for hit in selected)
                            if question["answerable"] else None)
            traces.append({
                "query_id": question["id"], "split": "dev", "config": config,
                "question": question["question"], "answerable": question["answerable"],
                "retrieval_strategy": "tfidf", "retrieval_top_k": 3,
                "retrieval_ids": [hit["id"] for hit in hits],
                "retrieval_scores": [hit["score"] for hit in hits],
                "selected_ids": ids,
                "selected_risks": {hit["id"]: review_risk(hit) for hit in selected},
                "omitted_ids": [hit["id"] for hit in hits if hit["id"] not in ids],
                "context": context, "context_chars": len(context),
                "context_minilm_tokens": tokens, "budget_chars": BUDGET_CHARS,
                "packing_ms": packing_ms, "retrieval_ms_from_frozen_run": retrieval["retrieval_ms"],
                "context_evidence": has_evidence,
            })
    metrics: dict[str, Any] = {
        "split": "dev", "question_count": len(questions),
        "answerable_count": sum(q["answerable"] for q in questions),
        "missing_evidence_count": sum(not q["answerable"] for q in questions),
        "retrieval_strategy": "tfidf", "retrieval_top_k": 3,
        "tokenizer": TOKENIZER_NAME, "token_meaning": "MiniLM WordPiece proxy; not LLM tokens",
        "configs": {},
    }
    denominator = metrics["answerable_count"]
    for config in CONFIGS:
        subset = [trace for trace in traces if trace["config"] == config]
        answerable = [trace for trace in subset if trace["answerable"]]
        evidence = sum(trace["context_evidence"] for trace in answerable)
        metrics["configs"][config] = {
            "budget_chars": BUDGET_CHARS, "token_budget": "not set; LLM not selected",
            "context_evidence_rate": {"count": evidence, "total": denominator,
                                      "rate": evidence / denominator},
            "mean_context_chars": statistics.mean(trace["context_chars"] for trace in subset),
            "max_context_chars": max(trace["context_chars"] for trace in subset),
            "mean_minilm_tokens": statistics.mean(trace["context_minilm_tokens"] for trace in subset),
            "max_minilm_tokens": max(trace["context_minilm_tokens"] for trace in subset),
            "mean_selected_chunks": statistics.mean(len(trace["selected_ids"]) for trace in subset),
            "median_packing_ms": statistics.median(trace["packing_ms"] for trace in subset),
            "mean_packing_ms": statistics.mean(trace["packing_ms"] for trace in subset),
            "service_cost_usd": 0, "hardware_cost_usd": "not measured",
        }
    return metrics, traces


def main() -> None:
    rows, hashes = approved_rows()
    questions, benchmark_sha256 = load_dev_benchmark(DEV_BENCHMARK, rows)
    locked = json.loads(BENCHMARK_MANIFEST.read_text(encoding="utf-8-sig"))
    if benchmark_sha256 != locked["dev"]["sha256"] or hashes["v2_sha256"] != locked["corpus_sha256"]:
        raise RuntimeError("Dev benchmark/corpus hash differs from locked manifest")
    tfidf, retrieval_sha256 = frozen_tfidf_traces(questions, rows)
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME, local_files_only=True)
    metrics, traces = run_contexts(questions, tfidf, tokenizer)
    output = ROOT / "starter/results/discrete_math_v2" / (
        "context-dev-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark_dev_sha256": benchmark_sha256, "corpus_hashes": hashes,
        "frozen_retrieval_traces_sha256": retrieval_sha256,
        "retrieval_strategy": "tfidf", "candidate_count_per_question": 3,
        "configs": {
            "C0": "original rank, greedy full cited chunks, 800 Unicode chars",
            "C1": "same Top-3, complete cited chunk subset selected by rank, content_type, query cue and extraction risk; 800 Unicode chars",
        },
        "gold_used_by_packer": False, "test_benchmark_opened": False,
        "database_accessed": False, "corpus_reembedded": False,
    }
    output.mkdir(parents=True, exist_ok=False)
    for name, data in (("metrics_auto.json", metrics), ("traces.json", traces),
                       ("run_manifest.json", manifest)):
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
    print(json.dumps({"output": str(output), "metrics": metrics}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
