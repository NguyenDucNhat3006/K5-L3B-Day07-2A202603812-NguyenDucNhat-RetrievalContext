"""Run A1 on the locked 17-question dev split only; preserve each completed trace."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics

from agent_a1 import run_a1_agent
from evaluate_retrieval_v2 import load_dev_benchmark
from retrieval_v2 import V2RetrievalSuite, approved_rows
from run_agent_v2_dev import load_local_env
from agent_v2 import OpenRouterChatClient

ROOT = Path(__file__).resolve().parents[1]


def a1_metrics(cases: list[dict], traces: list[dict], limits: dict) -> dict:
    if len(cases) != 17 or len(traces) != 17 or {c["id"] for c in cases} != {t["query_id"] for t in traces}:
        raise ValueError("A1 metrics require exactly the same 17 dev cases and traces")
    by_id = {c["id"]: c for c in cases}
    calls = sum(len(t["api_responses"]) for t in traces)
    tokens = {k: sum(t["token_usage"][k] for t in traces)
              for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    costs_known = all(t["actual_cost_usd"] is not None for t in traces)
    return {"configuration": "A1", "split": "dev", "n": 17,
        "answered": sum(t["status"] == "answered" for t in traces),
        "abstained": sum(t["status"] == "abstain" for t in traces),
        "tool_use_correct": {"n": sum(any(e["event"] == "search" for e in t["events"]) for t in traces), "N": 17},
        "failure_types": {key: sum(t["failure_type"] == key for t in traces) for key in
            ("model_abstention", "citation_validation_failure", "retrieval_failure", "repair_failure")},
        "repair": {"cases_repaired": sum(t["repair_count"] > 0 for t in traces),
                   "calls": sum(t["repair_count"] for t in traces)},
        "citation_structure_valid_answers": sum(t["status"] == "answered" for t in traces),
        "false_refusals_auto": sum(by_id[t["query_id"]]["answerable"] and t["status"] == "abstain" for t in traces),
        "correct_missing_evidence_abstentions_auto": sum((not by_id[t["query_id"]]["answerable"]) and t["status"] == "abstain" for t in traces),
        "grounded_answer": "requires_manual_audit",
        "semantic_citation_support": "requires_manual_audit",
        "latency_mean_ms": statistics.mean(t["latency_ms"] for t in traces),
        "latency_median_ms": statistics.median(t["latency_ms"] for t in traces),
        "tokens": tokens, "api_calls": calls,
        "actual_cost_usd": round(sum(t["actual_cost_usd"] or 0 for t in traces), 10) if costs_known else None,
        "budget_limits": limits,
        "budget_respected": calls <= limits["max_api_calls"] and tokens["total_tokens"] <= limits["max_total_tokens"] and
            (not costs_known or sum(t["actual_cost_usd"] or 0 for t in traces) <= limits["max_cost_usd"])}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-api-calls", type=int, default=51)
    parser.add_argument("--max-total-tokens", type=int, default=30000)
    parser.add_argument("--max-cost-usd", type=float, default=0.10)
    parser.add_argument("--max-completion-tokens", type=int, default=500)
    args = parser.parse_args()
    load_local_env(ROOT / ".env")
    model, key = os.getenv("LAB07_LLM_MODEL"), os.getenv("OPENROUTER_API_KEY")
    if not model or not key:
        raise SystemExit("OpenRouter model/key missing")
    if os.getenv("LAB07_EXTERNAL_CORPUS_OK") != "1":
        raise SystemExit("External document sharing permission is not enabled")
    if model != "z-ai/glm-5.3-flash:floor":
        raise SystemExit("A1 requires the frozen model z-ai/glm-5.3-flash:floor")
    rates = (float(os.environ["LAB07_INPUT_USD_PER_1M"]), float(os.environ["LAB07_OUTPUT_USD_PER_1M"]))
    if args.max_api_calls < 51 or args.max_total_tokens < 1 or args.max_cost_usd <= 0 or args.max_completion_tokens < 1:
        raise SystemExit("Insufficient or invalid A1 budget")
    rows, hashes = approved_rows()
    cases, bench_sha = load_dev_benchmark(ROOT / "data/benchmark_v2_dev.json", rows)
    if len(rows) != 332 or len(cases) != 17:
        raise RuntimeError("A1 locked V2/dev shape mismatch")
    suite = V2RetrievalSuite(rows, dense_backend=None)
    client = OpenRouterChatClient(model, key,
        base_url=os.getenv("LAB07_LLM_BASE_URL", "https://openrouter.ai/api/v1"), max_price=rates)
    run_dir = ROOT / "starter/results/discrete_math_v2" / ("agent-a1-dev-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run_dir.mkdir(parents=True, exist_ok=False)
    limits = {"max_api_calls": args.max_api_calls, "max_total_tokens": args.max_total_tokens,
              "max_cost_usd": args.max_cost_usd}
    manifest = {"run_id": run_dir.name, "configuration": "A1", "model": model,
        "retrieval": "TF-IDF Top-3", "context": "C0 <=800 Unicode chars", "chunk_count": 332,
        "v1_v2_hashes": hashes, "dev_benchmark_sha256": bench_sha, "limits": limits,
        "provider_price_caps_usd_per_million": rates, "max_repairs_per_question": 1,
        "test_benchmark_opened": False, "database_accessed": False}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    traces, calls, total_tokens, total_cost = [], 0, 0, 0.0
    for case in cases:
        if calls + 3 > args.max_api_calls or total_tokens + 3 * args.max_completion_tokens > args.max_total_tokens or total_cost >= args.max_cost_usd:
            break
        trace = run_a1_agent(case["question"], suite, client, max_tokens_per_call=args.max_completion_tokens,
                             rates_usd_per_million=rates)
        trace.update({"query_id": case["id"], "split": "dev"})
        traces.append(trace)
        calls += len(trace["api_responses"])
        total_tokens += trace["token_usage"]["total_tokens"]
        total_cost += trace["actual_cost_usd"] if trace["actual_cost_usd"] is not None else (trace["estimated_cost_usd"] or 0)
        (run_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if calls > args.max_api_calls or total_tokens > args.max_total_tokens or total_cost > args.max_cost_usd:
            break
    (run_dir / "metrics_auto.json").write_text(json.dumps(a1_metrics(cases[:len(traces)], traces, limits), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reviews = [{"query_id": t["query_id"], "answerable": next(c["answerable"] for c in cases if c["id"] == t["query_id"]),
                "answer_grade": None, "citation_support": [None] * len(t["citations"]),
                "abstention_correct": None, "reason": ""} for t in traces]
    (run_dir / "reviews_template.json").write_text(json.dumps(reviews, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
