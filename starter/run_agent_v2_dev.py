"""Guarded 17-question dev-only API runner. Never opens the test benchmark."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics

from agent_v2 import OpenRouterChatClient, run_v2_agent
from evaluate_retrieval_v2 import load_dev_benchmark
from retrieval_v2 import V2RetrievalSuite, approved_rows

ROOT = Path(__file__).resolve().parents[1]


def load_local_env(path: Path) -> None:
    """Load simple KEY=VALUE .env entries without echoing or replacing process env."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key not in {"OPENROUTER_API_KEY", "LAB07_LLM_MODEL", "LAB07_LLM_BASE_URL",
                       "LAB07_INPUT_USD_PER_1M", "LAB07_OUTPUT_USD_PER_1M",
                       "LAB07_EXTERNAL_CORPUS_OK"}:
            continue
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def metrics(cases: list[dict], traces: list[dict]) -> dict:
    by_id = {case["id"]: case for case in cases}
    if not traces or len(by_id) != len(traces):
        raise ValueError("case/trace count mismatch")
    if len({trace["query_id"] for trace in traces}) != len(traces):
        raise ValueError("duplicate trace ID")
    return {"split": "dev", "cases": len(traces), "configuration": "TF-IDF Top-3 + C0 800 chars",
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
            "actual_cost_usd": round(sum(t["actual_cost_usd"] or 0 for t in traces), 10)
                if all(t["actual_cost_usd"] is not None for t in traces) else None,
            "estimated_cost_usd": round(sum(t["estimated_cost_usd"] or 0 for t in traces), 10)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-api-calls", type=int, required=True)
    parser.add_argument("--max-total-tokens", type=int, required=True)
    parser.add_argument("--max-cost-usd", type=float, required=True)
    parser.add_argument("--max-completion-tokens", type=int, default=300)
    parser.add_argument("--limit", type=int, choices=(1, 17), default=1,
                        help="1 for a single dev smoke test; 17 only for a separately authorized full dev run")
    parser.add_argument("--question-id", help="Select one existing dev question, e.g. d04; requires --limit 1")
    args = parser.parse_args()
    load_local_env(ROOT / ".env")
    model, key = os.getenv("LAB07_LLM_MODEL"), os.getenv("OPENROUTER_API_KEY")
    if not model or not key:
        raise SystemExit("Set LAB07_LLM_MODEL and OPENROUTER_API_KEY before API evaluation")
    if os.getenv("LAB07_EXTERNAL_CORPUS_OK") != "1":
        raise SystemExit("Verify document API redistribution rights, then set LAB07_EXTERNAL_CORPUS_OK=1")
    try:
        rates = (float(os.environ["LAB07_INPUT_USD_PER_1M"]),
                 float(os.environ["LAB07_OUTPUT_USD_PER_1M"]))
    except (KeyError, ValueError) as exc:
        raise SystemExit("Set verified model input/output USD-per-million-token rates") from exc
    if (args.max_api_calls < 2 * args.limit or args.max_total_tokens < 1 or args.max_cost_usd <= 0
            or args.max_completion_tokens < 1 or any(rate < 0 for rate in rates)):
        raise SystemExit("Invalid API call, token, or cost limits")
    if args.question_id and args.limit != 1:
        raise SystemExit("--question-id requires --limit 1")
    rows, hashes = approved_rows()
    cases, benchmark_hash = load_dev_benchmark(ROOT / "data/benchmark_v2_dev.json", rows)
    if len(rows) != 332 or len(cases) != 17:
        raise ValueError("approved corpus/dev count changed")
    if args.question_id:
        cases = [case for case in cases if case["id"] == args.question_id]
        if len(cases) != 1:
            raise SystemExit("Unknown dev question ID")
    else:
        cases = cases[:args.limit]
    suite = V2RetrievalSuite(rows, dense_backend=None)
    client = OpenRouterChatClient(model, key, base_url=os.getenv("LAB07_LLM_BASE_URL", "https://openrouter.ai/api/v1"),
                              max_price=rates)
    run_dir = ROOT / "starter/results/discrete_math_v2" / ("agent-dev-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "manifest.json").write_text(json.dumps({"model": model, "corpus_hashes": hashes,
        "dev_benchmark_sha256": benchmark_hash, "configuration": "TF-IDF Top-3 + C0 800 chars",
        "max_api_calls": args.max_api_calls, "max_total_tokens": args.max_total_tokens,
        "max_cost_usd": args.max_cost_usd, "rates_usd_per_million": rates,
        "limit": args.limit, "base_url": client.base_url, "routing": "model suffix plus max_price and require_parameters",
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
        cost += trace["actual_cost_usd"] if trace["actual_cost_usd"] is not None else (trace["estimated_cost_usd"] or 0)
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
