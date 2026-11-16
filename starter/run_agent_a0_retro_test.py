"""One-pass A0 retrospective evaluation on the already-opened 7-case test.

This is deliberately not an independent test. It reuses A0's unchanged
run_v2_agent logic and freezes every input/source hash before its first request.
The one-shot sentinel remains after completion or interruption to prevent an
accidental second API pass.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
from datetime import datetime, timezone
from typing import Any

from agent_v2 import OpenRouterChatClient, SYSTEM, TOOL, run_v2_agent
from evaluate_retrieval_v2 import evidence_hit, evidence_in_text
from retrieval_v2 import V2RetrievalSuite, approved_rows
from run_agent_v2_dev import load_local_env
from run_agent_a1_test import key_status, load_test_cases

ROOT = Path(__file__).resolve().parents[1]
TEST_FILE = ROOT / "data/benchmark_v2_test.json"
BENCHMARK_MANIFEST = ROOT / "data/benchmark_v2_manifest.json"
RESULTS = ROOT / "starter/results/discrete_math_v2"
RUN_LIMITS = {"max_api_calls": 14, "max_total_tokens": 20_000, "max_cost_usd": 0.10}
MAX_COMPLETION_TOKENS = 300
MODEL_LOCKED = "z-ai/glm-5.3-flash:floor"
RATES_LOCKED = (0.042, 0.184)
SYSTEM_SHA256 = "15581527595b44a879acf2a65104a879e6ade6c2ab032b19cd966b0e19a16300"
HISTORICAL_REFS = (
    "c8a19d50396c052a5f4ee35ea4fb6bf42093edb6",
    "42aeb348878351ce36080dfde066d2a45df0c95d",
)
SOURCE_PATHS = (
    ROOT / "starter/run_agent_a0_retro_test.py",
    ROOT / "starter/agent_v2.py",
    ROOT / "starter/run_agent_v2_dev.py",
    ROOT / "starter/context_engineering_v2.py",
    ROOT / "starter/retrieval_v2.py",
    ROOT / "starter/evaluate_retrieval_v2.py",
    ROOT / "starter/baseline.py",
    ROOT / "starter/run_agent_a1_test.py",
    ROOT / ".gitignore",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def extract_constant(source: str, name: str) -> Any:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"Historical constant not found: {name}")


def historical_prompt_audit() -> dict[str, Any]:
    current_tool_hash = sha256_bytes(json.dumps(TOOL, sort_keys=True,
                                               ensure_ascii=False).encode("utf-8"))
    current_system_hash = sha256_bytes(SYSTEM.encode("utf-8"))
    if current_system_hash != SYSTEM_SHA256:
        raise RuntimeError("A0 system prompt no longer matches its recovered hash")
    ref_audits = []
    for ref in HISTORICAL_REFS:
        raw = subprocess.check_output(["git", "show", f"{ref}:starter/agent_v2.py"])
        source = raw.decode("utf-8")
        old_system = extract_constant(source, "SYSTEM")
        old_tool = extract_constant(source, "TOOL")
        system_hash = sha256_bytes(old_system.encode("utf-8"))
        tool_hash = sha256_bytes(json.dumps(old_tool, sort_keys=True,
                                            ensure_ascii=False).encode("utf-8"))
        if (system_hash != current_system_hash or tool_hash != current_tool_hash):
            raise RuntimeError("A0 prompt/tool differs from the recovered historical commits")
        ref_audits.append({"commit": ref, "agent_v2_blob_sha256": sha256_bytes(raw),
                           "system_prompt_sha256": system_hash, "tool_schema_sha256": tool_hash,
                           "system_and_tool_match_current": True})
    return {"current_system_prompt_sha256": current_system_hash,
            "current_tool_schema_sha256": current_tool_hash,
            "historical_commits": ref_audits,
            "historical_runner_and_api_adapter_exact_match_proven": False,
            "limitation": "A0 dev manifest omitted source hashes; current OpenRouter adapter/runner snapshot cannot be proven byte-identical to the original A0 dev execution."}


class GuardedClient:
    """Single-attempt API wrapper with conservative pre-call caps and no retry."""
    def __init__(self, client: OpenRouterChatClient, rates: tuple[float, float]):
        self.client = client
        self.rates = rates
        self.calls = 0
        self.total_tokens = 0
        self.actual_cost_total = 0.0
        self.actual_cost_known = True
        self.estimated_cost_total = 0.0
        self.responses: list[dict[str, Any]] = []

    def complete(self, messages, *, tools=None, max_tokens=400, json_mode=False):
        if self.calls >= RUN_LIMITS["max_api_calls"]:
            raise RuntimeError("API call hard cap reached; stopped before request")
        if max_tokens != MAX_COMPLETION_TOKENS:
            raise RuntimeError("Unexpected completion token cap")
        prompt_chars = len(json.dumps(messages, ensure_ascii=False))
        # Reserve one input token per serialized Unicode character plus the
        # locked output allowance. Actual provider usage remains the authority.
        token_reserve = prompt_chars + max_tokens
        if self.total_tokens + token_reserve > RUN_LIMITS["max_total_tokens"]:
            raise RuntimeError("Conservative total-token reserve exhausted; stopped before request")
        reserve_cost = (prompt_chars * self.rates[0] + max_tokens * self.rates[1]) / 1_000_000
        if self.estimated_cost_total + reserve_cost > RUN_LIMITS["max_cost_usd"]:
            raise RuntimeError("Conservative cost reserve exhausted; stopped before request")
        self.calls += 1
        result = self.client.complete(messages, tools=tools, max_tokens=max_tokens,
                                      json_mode=json_mode)
        usage = result.get("usage") or {}
        used = usage.get("total_tokens")
        if not isinstance(used, int) or used <= 0:
            raise RuntimeError("OpenRouter response lacks positive total token usage")
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        reported_cost = usage.get("cost")
        estimated_cost = (prompt_tokens * self.rates[0]
                          + completion_tokens * self.rates[1]) / 1_000_000
        self.total_tokens += used
        self.estimated_cost_total += estimated_cost
        if isinstance(reported_cost, (int, float)):
            self.actual_cost_total += float(reported_cost)
        else:
            self.actual_cost_known = False
        endpoints = ((result.get("openrouter_metadata") or {}).get("endpoints") or {})
        available = endpoints.get("available") or []
        self.responses.append({
            "id": result.get("id"), "model": result.get("model"),
            "provider_endpoints": available, "usage": usage,
            "content": result["choices"][0]["message"].get("content"),
            "tool_calls": result["choices"][0]["message"].get("tool_calls"),
            "estimated_cost_usd": round(estimated_cost, 10),
        })
        if (self.total_tokens > RUN_LIMITS["max_total_tokens"]
                or self.estimated_cost_total > RUN_LIMITS["max_cost_usd"]
                or (reported_cost is not None and self.actual_cost_total > RUN_LIMITS["max_cost_usd"])):
            raise RuntimeError("Observed usage exceeded a hard cap; stopped")
        return result


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def retrieval_metrics(cases: list[dict], traces: list[dict]) -> dict[str, Any]:
    by_id = {case["id"]: case for case in cases}
    eligible = [trace for trace in traces if by_id[trace["query_id"]]["answerable"]
                and trace.get("status") in ("answered", "abstain")]
    hit1 = hit3 = context_hit = 0
    for trace in eligible:
        gold = by_id[trace["query_id"]]["gold"]
        hits = trace.get("retrieval_hits", [])
        hit1 += int(bool(hits) and evidence_hit(hits[0], gold))
        hit3 += int(any(evidence_hit(hit, gold) for hit in hits[:3]))
        context_hit += int(any(item["chunk_id"] in trace.get("context_ids", [])
                               and evidence_in_text(item["evidence"], trace.get("selected_context", ""))
                               for item in gold))
    total = len(eligible)
    return {"answerable_completed": total,
            "hit_at_1": {"count": hit1, "total": total, "rate": hit1 / total if total else None},
            "evidence_hit_at_3": {"count": hit3, "total": total, "rate": hit3 / total if total else None},
            "context_evidence_rate": {"count": context_hit, "total": total,
                                      "rate": context_hit / total if total else None},
            "scoring": "Exact chunk ID/source/page plus whitespace-normalized gold evidence quote; quote must also appear in final C0 context for context hit."}


def auto_metrics(cases: list[dict], traces: list[dict], client: GuardedClient) -> dict[str, Any]:
    by_id = {case["id"]: case for case in cases}
    completed = [trace for trace in traces if trace.get("status") in ("answered", "abstain")]
    answerable = [trace for trace in completed if by_id[trace["query_id"]]["answerable"]]
    missing = [trace for trace in completed if not by_id[trace["query_id"]]["answerable"]]
    answered = [trace for trace in completed if trace["status"] == "answered"]
    latencies = [trace["latency_ms"] for trace in traces]
    counts = {key: sum(int(trace.get("token_usage", {}).get(key, 0)) for trace in traces)
              for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    providers: dict[str, int] = {}
    for response in client.responses:
        for endpoint in response.get("provider_endpoints", []):
            if endpoint.get("selected"):
                provider = endpoint.get("provider") or "unknown"
                providers[provider] = providers.get(provider, 0) + 1
    return {
        "split": "test", "agent": "A0", "retrospective_baseline": True,
        "independent_test": False, "expected_cases": 7, "completed_cases": len(completed),
        "failed_cases": len(traces) - len(completed), "answerable_completed": len(answerable),
        "missing_evidence_completed": len(missing), "answered": len(answered),
        "abstained": sum(trace.get("status") == "abstain" for trace in completed),
        "tool_use_correct": {"count": sum(any(event.get("event") == "search"
                                                  for event in trace.get("events", []))
                                             for trace in completed), "total": len(completed)},
        "citation_structure_valid": {"count": len(answered), "total_answered": len(answered),
                                     "total_cases": len(completed)},
        "grounded_answer_rate": "manual_audit_required",
        "semantic_citation_support": "manual_audit_required",
        "false_refusal_auto": {"count": sum(trace["status"] == "abstain" for trace in answerable),
                                "total": len(answerable)},
        "missing_evidence_abstention_auto": {
            "count": sum(trace["status"] == "abstain" for trace in missing), "total": len(missing)},
        "retrieval_metrics": retrieval_metrics(cases, traces),
        "latency_mean_ms": statistics.mean(latencies) if latencies else None,
        "latency_median_ms": statistics.median(latencies) if latencies else None,
        "token_usage": counts, "api_calls_attempted": client.calls,
        "api_responses_with_usage": len(client.responses), "provider_counts": providers,
        "actual_cost_usd": round(client.actual_cost_total, 10) if client.actual_cost_known else None,
        "estimated_cost_usd": round(client.estimated_cost_total, 10),
        "limits": {**RUN_LIMITS, "max_completion_tokens_per_call": MAX_COMPLETION_TOKENS},
        "observed_limits_respected": client.calls <= RUN_LIMITS["max_api_calls"]
            and client.total_tokens <= RUN_LIMITS["max_total_tokens"]
            and client.estimated_cost_total <= RUN_LIMITS["max_cost_usd"]
            and (not client.actual_cost_known or client.actual_cost_total <= RUN_LIMITS["max_cost_usd"]),
    }


def main() -> None:
    load_local_env(ROOT / ".env")
    model = os.getenv("LAB07_LLM_MODEL", "")
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    base_url = os.getenv("LAB07_LLM_BASE_URL", "https://openrouter.ai/api/v1")
    if model != MODEL_LOCKED or not api_key:
        raise SystemExit("Locked model or OpenRouter API key missing; no requests sent")
    if os.getenv("LAB07_EXTERNAL_CORPUS_OK") != "1":
        raise SystemExit("External corpus permission flag is not enabled; no requests sent")
    try:
        rates = (float(os.environ["LAB07_INPUT_USD_PER_1M"]),
                 float(os.environ["LAB07_OUTPUT_USD_PER_1M"]))
    except (KeyError, ValueError):
        raise SystemExit("Verified input/output price caps are missing; no requests sent") from None
    if rates != RATES_LOCKED:
        raise SystemExit("Price caps differ from frozen A1 model configuration; no requests sent")

    prompt_audit = historical_prompt_audit()
    rows, corpus_hashes = approved_rows()
    benchmark_manifest = json.loads(BENCHMARK_MANIFEST.read_text(encoding="utf-8-sig"))
    if len(rows) != 332 or corpus_hashes["v2_sha256"] != benchmark_manifest["corpus_sha256"]:
        raise RuntimeError("V2 corpus count/hash differs from the approved manifest")
    cases, test_hash = load_test_cases(TEST_FILE, rows, benchmark_manifest["test"]["sha256"])
    if len(cases) != 7 or sum(case["answerable"] for case in cases) != 5:
        raise RuntimeError("Locked test split shape changed")
    key_limits = key_status(api_key, base_url)
    remaining = key_limits.get("limit_remaining")
    if not isinstance(remaining, (int, float)) or remaining < RUN_LIMITS["max_cost_usd"]:
        raise SystemExit("OpenRouter spend limit does not cover $0.10; no LLM requests sent")

    # A persistent one-shot sentinel prevents an accidental second execution.
    RESULTS.mkdir(parents=True, exist_ok=True)
    sentinel = RESULTS / ".a0-retro-test-one-shot.lock"
    try:
        with sentinel.open("x", encoding="utf-8") as stream:
            stream.write("A0 retrospective test pass authorized once; do not rerun.\n")
    except FileExistsError:
        raise SystemExit("One-shot A0 retrospective sentinel exists; refusing to rerun") from None

    now = datetime.now(timezone.utc)
    run_dir = RESULTS / ("agent-a0-retro-test-" + now.strftime("%Y%m%dT%H%M%S%fZ"))
    run_dir.mkdir(parents=False, exist_ok=False)
    source_hashes = {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path)
                     for path in SOURCE_PATHS}
    manifest = {
        "run_id": run_dir.name, "created_utc": now.isoformat(), "split": "test",
        "retrospective_baseline": True, "independent_test": False,
        "test_was_previously_opened": True,
        "configuration": {"agent": "A0 pre-A1 run_v2_agent", "system_prompt": "agent_v2.SYSTEM",
            "tool_schema": "agent_v2.TOOL", "model": model,
            "provider_routing": "OpenRouter model suffix :floor; require_parameters; configured provider.max_price",
            "retriever": "TF-IDF Top-3", "context": "C0 <=800 Unicode characters",
            "corpus": "Discrete Math V2", "chunk_count": 332, "repair_calls": 0,
            "max_completion_tokens_per_call": MAX_COMPLETION_TOKENS},
        "historical_reconstruction": prompt_audit,
        "permission_preflight": {"user_approved_this_single_retrospective_run": True,
            "external_corpus_flag_enabled": True,
            "basis": "User authorization for this run plus previously attested permission to submit the Lab 07 corpus for external evaluation; this does not authorize public redistribution.",
            "openrouter_key_validated_read_only": True,
            "provider_spending_limit_covers_run_cap": True},
        "limits": {**RUN_LIMITS, "max_completion_tokens_per_call": MAX_COMPLETION_TOKENS,
                   "provider_spending_limit_must_cover": RUN_LIMITS["max_cost_usd"]},
        "configured_price_caps_usd_per_million": {"input": rates[0], "output": rates[1]},
        "hashes": {"test_benchmark_sha256": test_hash,
            "corpus_v2_sha256": corpus_hashes["v2_sha256"],
            "benchmark_manifest_sha256": sha256_file(BENCHMARK_MANIFEST),
            "source_files_sha256": source_hashes,
            "a0_system_prompt_sha256": prompt_audit["current_system_prompt_sha256"],
            "a0_tool_schema_sha256": prompt_audit["current_tool_schema_sha256"],
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()},
        "question_count": 7, "answerable_count": 5, "missing_evidence_count": 2,
        "database_accessed": False, "database_written": False, "embeddings_created": 0,
        "run_status": "locked_pre_api", "failure": None,
    }
    write_json(run_dir / "manifest.json", manifest)
    write_json(run_dir / "traces.json", [])
    write_json(run_dir / "metrics_auto_partial.json", {"status": "no_cases_completed"})

    suite = V2RetrievalSuite(rows, dense_backend=None)
    client = OpenRouterChatClient(model, api_key, base_url=base_url, max_price=rates)
    guarded = GuardedClient(client, rates)
    traces: list[dict] = []
    reviews: list[dict] = []
    failure = None
    # The test set is evaluated exactly once in its frozen file order. No
    # benchmark labels are sent to the agent or retrieval tool.
    for index, case in enumerate(cases, start=1):
        call_start = guarded.calls
        response_start = len(guarded.responses)
        started = time.perf_counter()
        try:
            trace = run_v2_agent(case["question"], suite, guarded,
                                 max_tokens_per_call=MAX_COMPLETION_TOKENS,
                                 rates_usd_per_million=rates)
            trace.update({"query_id": case["id"], "split": "test", "case_index": index})
        except Exception as exc:
            case_responses = guarded.responses[response_start:]
            case_usage = {key: sum(int((response.get("usage") or {}).get(key, 0))
                                   for response in case_responses)
                          for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
            trace = {"query_id": case["id"], "split": "test", "case_index": index,
                "question": case["question"], "status": "error", "failure_type": "api_or_budget_error",
                "error_type": type(exc).__name__, "error": str(exc).replace(api_key, "[redacted]")[:400],
                "api_calls_attempted": guarded.calls - call_start,
                "api_response_details": case_responses, "latency_ms": (time.perf_counter()-started)*1000,
                "token_usage": case_usage}
            traces.append(trace)
            failure = {"query_id": case["id"], "error_type": type(exc).__name__,
                       "call_count": guarded.calls}
            write_json(run_dir / "traces.json", traces)
            write_json(run_dir / "metrics_auto_partial.json", auto_metrics(cases, traces, guarded))
            break
        trace["api_calls_attempted"] = guarded.calls - call_start
        trace["api_response_details"] = guarded.responses[response_start:]
        trace["retrospective_baseline"] = True
        traces.append(trace)
        write_json(run_dir / "traces.json", traces)
        write_json(run_dir / "metrics_auto_partial.json", auto_metrics(cases, traces, guarded))
        reviews.append({"query_id": case["id"], "answerable": case["answerable"],
            "answer_grade": None, "citation_structure_valid": trace.get("status") == "answered",
            "citation_semantic_support": [None] * len(trace.get("citations", [])),
            "abstention_correct": None, "context_grade": None, "reason": "pending manual PDF audit"})
        write_json(run_dir / "reviews_template.json", reviews)

    manifest["run_status"] = "complete" if len(traces) == len(cases) and not failure else "partial"
    manifest["failure"] = failure
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(run_dir / "manifest.json", manifest)
    metrics = auto_metrics(cases, traces, guarded)
    write_json(run_dir / "metrics_auto.json", metrics)
    result = {"run_dir": str(run_dir), "status": manifest["run_status"],
              "completed_cases": sum(trace.get("status") in ("answered", "abstain") for trace in traces),
              "trace_cases": len(traces), "api_calls_attempted": guarded.calls,
              "tokens_observed": guarded.total_tokens,
              "actual_cost_usd": metrics["actual_cost_usd"],
              "estimated_cost_usd": metrics["estimated_cost_usd"], "failure_type": failure and failure["error_type"]}
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
