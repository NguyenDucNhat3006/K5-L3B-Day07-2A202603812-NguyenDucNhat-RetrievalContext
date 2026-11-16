"""Guarded 17-question dev-only API runner. Never opens the test benchmark."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics

from agent_v2 import OpenAIChatClient, run_v2_agent
from evaluate_retrieval_v2 import load_dev_benchmark
from retrieval_v2 import V2RetrievalSuite, approved_rows

ROOT = Path(__file__).resolve().parents[1]


def metrics(cases: list[dict], traces: list[dict]) -> dict:
    by_id = {case["id"]: case for case in cases}
    if len(by_id) != 17 or len(traces) != 17:
        raise ValueError("dev run requires exactly 17 unique cases and traces")
    if len({trace["query_id"] for trace in traces}) != 17:
        raise ValueError("duplicate trace ID")
    return {"split": "dev", "cases": 17, "configuration": "TF-IDF Top-3 + C0 800 chars",
            "answered": sum(t["status"] == "answered" for t in traces),
            "abstained": sum(t["status"] == "abstain" for t in traces),
            "tool_use_correct": sum(any(e["event"] == "search" for e in t["events"])
                                    for t in traces),
            "citation_structure_valid": sum(t["status"] == "answered" for t in traces),
            "missing_evidence_abstentions": sum(not by_id[t["query_id"]]["answerable"] and
                                                t["status"] == "abstain" for t in traces),
            "false_refusals": sum(by_id[t["query_id"]]["answerable"] and
                                  t["status"] == "abstain" for t in traces),
            "grounded_answer": "requires_manual_review",
            "citation_semantic_support": "requires_manual_review",
            "median_latency_ms": statistics.median(t["latency_ms"] for t in traces),
            "total_token_usage": {key: sum(t["token_usage"][key] for t in traces)
                                  for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
            "estimated_cost_usd": round(sum(t["estimated_cost_usd"] or 0 for t in traces), 8)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-api-calls", type=int, required=True)
    parser.add_argument("--max-total-tokens", type=int, required=True)
    parser.add_argument("--max-cost-usd", type=float, required=True)
    parser.add_argument("--max-completion-tokens", type=int, default=300)
    args = parser.parse_args()
    model, key = os.getenv("LAB07_LLM_MODEL"), os.getenv("OPENAI_API_KEY")
    if not model or not key:
        raise SystemExit("Set LAB07_LLM_MODEL and OPENAI_API_KEY before API evaluation")
    if os.getenv("LAB07_EXTERNAL_CORPUS_OK") != "1":
        raise SystemExit("Verify document API redistribution rights, then set LAB07_EXTERNAL_CORPUS_OK=1")
    try:
        rates = (float(os.environ["LAB07_INPUT_USD_PER_1M"]),
                 float(os.environ["LAB07_OUTPUT_USD_PER_1M"]))
    except (KeyError, ValueError) as exc:
        raise SystemExit("Set verified model input/output USD-per-million-token rates") from exc
    if (args.max_api_calls < 34 or args.max_total_tokens < 1 or args.max_cost_usd <= 0
            or args.max_completion_tokens < 1 or any(rate < 0 for rate in rates)):
        raise SystemExit("Invalid API call, token, or cost limits (17 cases need up to 34 calls)")
    rows, hashes = approved_rows()
    cases, benchmark_hash = load_dev_benchmark(ROOT / "data/benchmark_v2_dev.json", rows)
    if len(rows) != 332 or len(cases) != 17:
        raise ValueError("approved corpus/dev count changed")
    suite = V2RetrievalSuite(rows, dense_backend=None)
    client = OpenAIChatClient(model, key)
    run_dir = ROOT / "starter/results/discrete_math_v2" / ("agent-dev-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "manifest.json").write_text(json.dumps({"model": model, "corpus_hashes": hashes,
        "dev_benchmark_sha256": benchmark_hash, "configuration": "TF-IDF Top-3 + C0 800 chars",
        "max_api_calls": args.max_api_calls, "max_total_tokens": args.max_total_tokens,
        "max_cost_usd": args.max_cost_usd, "rates_usd_per_million": rates,
        "test_benchmark_opened": False, "database_accessed": False}, ensure_ascii=False, indent=2), encoding="utf-8")
    traces: list[dict] = []
    calls = 0
    tokens = 0
    cost = 0.0
    for case in cases:
        if calls + 2 > args.max_api_calls or tokens + 2 * args.max_completion_tokens > args.max_total_tokens or cost >= args.max_cost_usd:
            raise RuntimeError(f"API limit reached; partial traces in {run_dir}")
        trace = run_v2_agent(case["question"], suite, client,
                             max_tokens_per_call=args.max_completion_tokens,
                             rates_usd_per_million=rates)
        trace["query_id"] = case["id"]
        trace["split"] = "dev"
        traces.append(trace)
        calls += 1 + any(e["event"] == "llm_response" for e in trace["events"])
        tokens += trace["token_usage"]["total_tokens"]
        cost += trace["estimated_cost_usd"] or 0
        (run_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if tokens > args.max_total_tokens or cost > args.max_cost_usd:
            raise RuntimeError(f"API limit exceeded; partial traces in {run_dir}")
    (run_dir / "metrics_auto.json").write_text(json.dumps(metrics(cases, traces), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    review_template = [{"query_id": t["query_id"], "answerable": next(c["answerable"] for c in cases if c["id"] == t["query_id"]),
                        "answer_grade": None, "citation_support": [None] * len(t["citations"]),
                        "abstention_correct": None, "reason": ""} for t in traces]
    (run_dir / "reviews_template.json").write_text(json.dumps(review_template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
