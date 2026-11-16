"""One-shot, test-only A1 final evaluation with per-question durable traces.

This runner locks the config and input hashes before making any chat-completion
request. It never reads dev questions and never retries an API request.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from agent_a1 import run_a1_agent
from agent_v2 import OpenRouterChatClient
from context_engineering_v2 import pack_c0
from retrieval_v2 import V2RetrievalSuite, approved_rows
from run_agent_v2_dev import load_local_env

ROOT = Path(__file__).resolve().parents[1]
TEST_BENCHMARK = ROOT / "data/benchmark_v2_test.json"
LOCK_MANIFEST = ROOT / "data/benchmark_v2_manifest.json"
RUN_LIMITS = {"max_api_calls": 21, "max_total_tokens": 20_000, "max_cost_usd": 0.10}
MAX_COMPLETION_TOKENS = 300
SOURCE_FILES = (
    ROOT / "starter/agent_a1.py", ROOT / "starter/agent_v2.py",
    ROOT / "starter/context_engineering_v2.py", ROOT / "starter/retrieval_v2.py",
    ROOT / "starter/baseline.py", ROOT / "starter/run_agent_a1_test.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_test_cases(path: Path, rows: list[dict[str, Any]], expected_sha: str) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha:
        raise RuntimeError("Test benchmark hash differs from locked manifest")
    cases = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(cases, list) or len(cases) != 7:
        raise ValueError("Locked test split must contain exactly seven cases")
    ids: set[str] = set()
    for case in cases:
        if (not isinstance(case, dict) or case.get("split") != "test"
                or not isinstance(case.get("id"), str) or case["id"] in ids
                or not isinstance(case.get("question"), str) or not case["question"].strip()
                or not isinstance(case.get("answerable"), bool)):
            raise ValueError("Malformed or duplicate locked test case")
        ids.add(case["id"])
        if case["answerable"]:
            if not case.get("gold") or not isinstance(case.get("expected_answer"), str):
                raise ValueError(f"Answerable test case is malformed: {case['id']}")
            for item in case["gold"]:
                row = next((r for r in rows if r["id"] == item.get("chunk_id")), None)
                if (row is None or row["source_id"] != item.get("source_id")
                        or row["page"] != item.get("page")
                        or " ".join(item.get("evidence", "").split()) not in " ".join(row["text"].split())):
                    raise ValueError(f"Locked test gold fails V2 evidence validation: {case['id']}")
        elif case.get("gold") or case.get("expected_answer"):
            raise ValueError(f"Unanswerable case contains gold answer material: {case['id']}")
    if sum(c["answerable"] for c in cases) != 5 or sum(not c["answerable"] for c in cases) != 2:
        raise ValueError("Locked test split must have exactly five answerable and two absent cases")
    return cases, digest


def key_status(api_key: str, base_url: str) -> dict[str, Any]:
    request = Request(base_url.rstrip("/") + "/key",
                      headers={"Authorization": "Bearer " + api_key,
                               "Accept": "application/json"})
    # Read-only key metadata request. It never contains document context and
    # does not consume an LLM completion call.
    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8")).get("data", {})
    allowed = ("limit", "limit_remaining", "limit_reset", "usage", "is_free_tier")
    return {key: data.get(key) for key in allowed}


class BudgetedClient:
    """No-retry client wrapper with conservative pre-call token/cost reserves."""
    def __init__(self, client: OpenRouterChatClient, limits: dict, rates: tuple[float, float]):
        self.client = client
        self.limits = limits
        self.rates = rates
        self.calls = 0
        self.known_tokens = 0
        self.actual_cost = 0.0
        self.estimated_cost = 0.0
        self.responses: list[dict[str, Any]] = []

    @property
    def base_url(self):
        return self.client.base_url

    def complete(self, messages, *, tools=None, max_tokens=400, json_mode=False):
        if self.calls >= self.limits["max_api_calls"]:
            raise RuntimeError("API call budget would be exceeded")
        prompt_chars = len(json.dumps(messages, ensure_ascii=False))
        # Reserve half the serialized Unicode characters as prompt tokens. This
        # is deliberately conservative for Vietnamese text while leaving room
        # for the exact provider usage returned after each call.
        prompt_reserve = math.ceil(prompt_chars / 2)
        token_reserve = prompt_reserve + max_tokens
        if self.known_tokens + token_reserve > self.limits["max_total_tokens"]:
            raise RuntimeError("Conservative token reserve exceeds run budget")
        cost_reserve = ((prompt_reserve * self.rates[0]) + (max_tokens * self.rates[1])) / 1_000_000
        if self.estimated_cost + cost_reserve > self.limits["max_cost_usd"]:
            raise RuntimeError("Conservative cost reserve exceeds run budget")
        self.calls += 1
        response = self.client.complete(messages, tools=tools, max_tokens=max_tokens,
                                        json_mode=json_mode)
        usage = response.get("usage") or {}
        used = sum(int(usage.get(k, 0)) for k in ("prompt_tokens", "completion_tokens", "total_tokens"))
        # total_tokens is already prompt+completion; use it once.
        used = int(usage.get("total_tokens", 0))
        if used <= 0:
            raise RuntimeError("Response had no positive total token usage")
        rate_cost = (int(usage.get("prompt_tokens", 0)) * self.rates[0]
                     + int(usage.get("completion_tokens", 0)) * self.rates[1]) / 1_000_000
        reported = (usage.get("cost") if isinstance(usage.get("cost"), (int, float)) else None)
        self.known_tokens += used
        self.estimated_cost += rate_cost
        if reported is not None:
            self.actual_cost += float(reported)
        self.responses.append({"id": response.get("id"), "model": response.get("model"),
            "provider": (((response.get("openrouter_metadata") or {}).get("endpoints") or {})
                         .get("available") or []), "usage": usage,
            "content": response["choices"][0]["message"].get("content"),
            "tool_calls": response["choices"][0]["message"].get("tool_calls")})
        if (self.calls > self.limits["max_api_calls"]
                or self.known_tokens > self.limits["max_total_tokens"]
                or self.estimated_cost > self.limits["max_cost_usd"]
                or (reported is not None and self.actual_cost > self.limits["max_cost_usd"])):
            raise RuntimeError("Observed API usage exceeded a run budget; stopped")
        return response


def auto_metrics(cases: list[dict], traces: list[dict], limits: dict) -> dict:
    by_id = {case["id"]: case for case in cases}
    completed = [t for t in traces if t.get("status") in ("answered", "abstain")]
    answers = [t for t in completed if t["status"] == "answered"]
    absent = [t for t in completed if not by_id[t["query_id"]]["answerable"]]
    answerable = [t for t in completed if by_id[t["query_id"]]["answerable"]]
    totals = {key: sum(t.get("token_usage", {}).get(key, 0) for t in traces)
              for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    responses = [response for t in traces for response in t.get("api_responses", [])]
    provider_counts: dict[str, int] = {}
    for response in responses:
        for endpoint in response.get("provider_endpoints", []):
            if endpoint.get("selected"):
                name = endpoint.get("provider") or "unknown"
                provider_counts[name] = provider_counts.get(name, 0) + 1
    actual_known = all(t.get("actual_cost_usd") is not None for t in completed)
    actual_cost = sum(float(t.get("actual_cost_usd") or 0) for t in completed) if actual_known else None
    latencies = [t["latency_ms"] for t in completed]
    return {"split": "test", "configuration": "A1 + R0 TF-IDF Top-3 + C0 <=800 Unicode chars",
        "expected_cases": 7, "completed_cases": len(completed), "failed_cases": len(traces)-len(completed),
        "answerable_cases_completed": len(answerable), "unanswerable_cases_completed": len(absent),
        "answered": len(answers), "abstained": sum(t["status"] == "abstain" for t in completed),
        "tool_use_correct": {"count": sum(any(e.get("event") == "search" for e in t.get("events", []))
                                            for t in completed), "total": len(completed)},
        "citation_structure_valid": {"count": len(answers), "total": len(completed)},
        "false_refusal_auto": {"count": sum(t["status"] == "abstain" for t in answerable),
                               "total": sum(by_id[t["query_id"]]["answerable"] for t in completed)},
        "missing_evidence_abstention_auto": {"count": sum(t["status"] == "abstain" for t in absent),
                                             "total": sum(not by_id[t["query_id"]]["answerable"] for t in completed)},
        "grounded_answer_rate": "manual_audit_required",
        "semantic_citation_support": "manual_audit_required",
        "latency_mean_ms": statistics.mean(latencies) if latencies else None,
        "latency_median_ms": statistics.median(latencies) if latencies else None,
        "token_usage": totals, "api_calls": len(responses), "provider_counts": provider_counts,
        "actual_cost_usd": round(actual_cost, 10) if actual_cost is not None else None,
        "estimated_cost_usd_from_configured_rates": round(sum(
            (r.get("usage", {}).get("prompt_tokens", 0) * RUN_RATES[0]
             + r.get("usage", {}).get("completion_tokens", 0) * RUN_RATES[1]) / 1_000_000
            for r in responses), 10),
        "limits": limits,
        "observed_budget_respected": len(responses) <= limits["max_api_calls"]
            and totals["total_tokens"] <= limits["max_total_tokens"]
            and (actual_cost is None or actual_cost <= limits["max_cost_usd"])}


RUN_RATES = (0.042, 0.184)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run exactly one locked A1 test pass")
    parser.add_argument("--max-api-calls", type=int, default=21)
    parser.add_argument("--max-total-tokens", type=int, default=20_000)
    parser.add_argument("--max-cost-usd", type=float, default=0.10)
    args = parser.parse_args()
    if (args.max_api_calls != 21 or args.max_total_tokens != 20_000
            or not math.isclose(args.max_cost_usd, 0.10)):
        raise SystemExit("Final evaluation limits are locked to 21 calls, 20,000 tokens, and $0.10")

    load_local_env(ROOT / ".env")
    model = os.getenv("LAB07_LLM_MODEL", "")
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    base_url = os.getenv("LAB07_LLM_BASE_URL", "https://openrouter.ai/api/v1")
    if model != "z-ai/glm-5.3-flash:floor" or not api_key:
        raise SystemExit("Locked model or OpenRouter API key missing")
    if os.getenv("LAB07_EXTERNAL_CORPUS_OK") != "1":
        raise SystemExit("Document sharing permission flag is not enabled; no test calls sent")
    try:
        rates = (float(os.environ["LAB07_INPUT_USD_PER_1M"]),
                 float(os.environ["LAB07_OUTPUT_USD_PER_1M"]))
    except (KeyError, ValueError):
        raise SystemExit("Verified model input/output price caps are missing") from None
    if rates != RUN_RATES:
        raise SystemExit("Pricing caps differ from the frozen A1 model configuration")

    rows, corpus_hashes = approved_rows()
    benchmark_manifest = json.loads(LOCK_MANIFEST.read_text(encoding="utf-8-sig"))
    if (len(rows) != 332 or corpus_hashes["v2_sha256"] != benchmark_manifest["corpus_sha256"]):
        raise RuntimeError("Approved V2 corpus/hash changed")
    cases, test_hash = load_test_cases(TEST_BENCHMARK, rows, benchmark_manifest["test"]["sha256"])
    key_limits = key_status(api_key, base_url)
    remaining = key_limits.get("limit_remaining")
    if not isinstance(remaining, (int, float)) or remaining < args.max_cost_usd:
        raise SystemExit("OpenRouter key spending limit is absent or has less than $0.10 remaining")

    source_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in SOURCE_FILES}
    created = datetime.now(timezone.utc)
    run_dir = ROOT / "starter/results/discrete_math_v2" / (
        "agent-a1-final-test-" + created.strftime("%Y%m%dT%H%M%S%fZ"))
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "run_id": run_dir.name, "created_utc": created.isoformat(), "split": "test",
        "one_pass_only": True, "configuration": {"agent": "A1", "retriever": "R0 TF-IDF Top-3",
            "context": "C0 <=800 Unicode characters", "model": model,
            "provider_routing": "OpenRouter; model :floor route; require_parameters; configured provider.max_price",
            "corpus": "Discrete Math V2", "chunk_count": 332,
            "max_repairs_per_question": 1, "max_completion_tokens_per_call": MAX_COMPLETION_TOKENS},
        "permission_preflight": {"env_flag_enabled": True,
            "basis": "User previously attested document-sharing rights for OpenRouter dev evaluation; same approved corpus excerpts; flag enabled.",
            "source_manifest_permission_field": benchmark_manifest.get("source_redistribution_permission"),
            "external_context_sent_only_after_preflight": True},
        "openrouter_key_limit_preflight": key_limits,
        "limits": RUN_LIMITS,
        "configured_price_caps_usd_per_million": {"input": rates[0], "output": rates[1]},
        "hashes": {"test_benchmark_sha256": test_hash, "corpus_v2_sha256": corpus_hashes["v2_sha256"],
            "benchmark_manifest_sha256": sha256(LOCK_MANIFEST), "source_files_sha256": source_hashes,
            "a1_system_prompt_sha256": hashlib.sha256(__import__("agent_a1").A1_SYSTEM.encode()).hexdigest(),
            "a1_repair_prompt_sha256": hashlib.sha256(__import__("agent_a1").REPAIR_SYSTEM.encode()).hexdigest()},
        "question_count": len(cases), "answerable_count": 5, "missing_evidence_count": 2,
        "database_accessed": False, "database_written": False, "embeddings_created": 0,
        "dev_benchmark_opened": False, "test_questions_sent_once": True,
        "run_status": "preflight_passed_calls_not_started"}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (run_dir / "traces.json").write_text("[]\n", encoding="utf-8")
    suite = V2RetrievalSuite(rows, dense_backend=None)
    client = OpenRouterChatClient(model, api_key, base_url=base_url, max_price=rates)
    guarded = BudgetedClient(client, RUN_LIMITS, rates)
    traces: list[dict] = []
    failure = None
    for index, case in enumerate(cases, start=1):
        start = time.perf_counter()
        try:
            trace = run_a1_agent(case["question"], suite, guarded,
                                 max_tokens_per_call=MAX_COMPLETION_TOKENS,
                                 rates_usd_per_million=rates)
            trace.update({"query_id": case["id"], "split": "test", "case_index": index})
        except Exception as exc:
            failure = {"case_id": case["id"], "error_type": type(exc).__name__,
                       "error": str(exc)[:400], "call_count_so_far": guarded.calls}
            trace = {"query_id": case["id"], "split": "test", "case_index": index,
                "question": case["question"], "status": "error", "failure_type": "api_or_budget_error",
                "error_type": type(exc).__name__, "error": str(exc)[:400],
                "partial_api_responses": guarded.responses, "latency_ms": (time.perf_counter()-start)*1000,
                "token_usage": {key: sum(int((r.get("usage") or {}).get(key, 0))
                    for r in guarded.responses) for key in
                    ("prompt_tokens", "completion_tokens", "total_tokens")},
                "api_responses": []}
            traces.append(trace)
            break
        # Exact per-call response metadata, actual provider, and usage are kept.
        trace["api_responses"] = [{"id": r.get("id"), "model": r.get("model"),
            "provider_endpoints": r.get("provider", []), "usage": r.get("usage"),
            "content": r.get("content"), "tool_calls": r.get("tool_calls")}
            for r in guarded.responses[-len(trace["api_responses"]):]] if trace["api_responses"] else []
        traces.append(trace)
        (run_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        partial_metrics = auto_metrics(cases, traces, RUN_LIMITS)
        (run_dir / "metrics_auto_partial.json").write_text(json.dumps(partial_metrics, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    manifest["run_status"] = "complete" if len(traces) == len(cases) and not failure else "partial"
    manifest["failure"] = failure
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    metrics = auto_metrics(cases, traces, RUN_LIMITS)
    (run_dir / "metrics_auto.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (run_dir / "reviews_template.json").write_text(json.dumps([
        {"query_id": case["id"], "answerable": case["answerable"], "answer_grade": None,
         "citation_support": [None] * len(next((t.get("citations", []) for t in traces if t["query_id"] == case["id"]), [])),
         "abstention_correct": None, "reason": ""}
        for case in cases if any(t["query_id"] == case["id"] and t.get("status") != "error" for t in traces)
    ], ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "status": manifest["run_status"],
                      "completed_or_failed_cases": len(traces), "api_calls": guarded.calls,
                      "tokens_observed": guarded.known_tokens,
                      "openrouter_key_remaining_preflight_usd": remaining,
                      "failure": failure}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
