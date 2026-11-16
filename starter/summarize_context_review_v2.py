"""Validate human dev context reviews and summarize them without rewriting a run."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

from context_engineering_v2 import ROOT, citation_block
from retrieval_v2 import approved_rows

RUN = ROOT / "starter/results/discrete_math_v2/context-dev-20261116T044835296260Z"
AUDIT = ROOT / "report/individual/context_engineering_dev_audit.json"
VALID_REVIEW_STATES = {
    "none", "readable_sufficient", "readable_but_insufficient",
    "flagged_extra_not_used", "material_missing_for_question",
}


def _normalize(text: str) -> str:
    return " ".join(text.split())


def summarize(audit: dict, traces: list[dict], rows: list[dict]) -> dict:
    by_trace = {(trace["query_id"], trace["config"]): trace for trace in traces}
    if len(traces) != 34 or len(by_trace) != 34:
        raise ValueError("Expected exactly 17 dev questions x 2 context configurations")
    by_chunk = {row["id"]: row for row in rows}
    cases = audit.get("cases")
    if not isinstance(cases, list) or len(cases) != 17:
        raise ValueError("Manual audit must contain 17 dev cases")
    seen: set[str] = set()
    expanded: list[dict] = []
    for case in cases:
        query_id = case.get("query_id")
        if query_id in seen or (query_id, "C0") not in by_trace:
            raise ValueError(f"Duplicate or unknown audit case: {query_id}")
        seen.add(query_id)
        for config in ("C0", "C1"):
            trace = by_trace[(query_id, config)]
            if trace["answerable"] is not case.get("answerable"):
                raise ValueError(f"Answerability mismatch: {query_id}")
            review = case.get(config)
            if not isinstance(review, dict):
                raise ValueError(f"Missing {config} review for {query_id}")
            if "same_as" in review:
                if (config != "C1" or review != {"same_as": "C0"}
                        or trace["context"] != by_trace[(query_id, "C0")]["context"]):
                    raise ValueError(f"same_as is invalid for {query_id}")
                review = case["C0"]
            if review.get("needs_review_status") not in VALID_REVIEW_STATES:
                raise ValueError(f"Unknown review status: {query_id} {config}")
            if not isinstance(review.get("reason"), str) or not review["reason"].strip():
                raise ValueError(f"Missing review reason: {query_id} {config}")
            support_ids = review.get("support_ids")
            if not isinstance(support_ids, list) or any(
                item not in trace["selected_ids"] for item in support_ids
            ):
                raise ValueError(f"Support citation not in context: {query_id} {config}")
            for chunk_id in trace["selected_ids"]:
                row = by_chunk.get(chunk_id)
                if row is None or citation_block(row) not in trace["context"]:
                    raise ValueError(f"Context citation differs from V2: {query_id} {config}")
            status = review["needs_review_status"]
            flagged = [chunk_id for chunk_id, risk in trace["selected_risks"].items()
                       if risk != "ok"]
            if status in ("material_missing_for_question", "readable_but_insufficient",
                          "flagged_extra_not_used", "readable_sufficient") and not flagged:
                raise ValueError(f"Review state needs a flagged chunk: {query_id} {config}")
            if status == "flagged_extra_not_used" and not set(flagged) - set(support_ids):
                raise ValueError(f"No unused flagged chunk: {query_id} {config}")
            if status == "readable_sufficient" and not set(flagged) & set(support_ids):
                raise ValueError(f"No supporting flagged chunk: {query_id} {config}")
            if trace["answerable"]:
                grade = review.get("grade")
                if type(grade) is not int or grade not in (0, 1, 2):
                    raise ValueError(f"Invalid rubric grade: {query_id} {config}")
                if grade == 0 and support_ids:
                    raise ValueError(f"Grade 0 cannot have supporting evidence: {query_id}")
                if grade > 0 and not support_ids:
                    raise ValueError(f"Positive grade needs a citation: {query_id}")
                excerpt = review.get("excerpt")
                if (grade > 0 and (not isinstance(excerpt, str) or
                                  _normalize(excerpt) not in _normalize(trace["context"]))):
                    raise ValueError(f"Supporting excerpt absent from context: {query_id}")
            else:
                if review.get("grade") is not None or support_ids or not isinstance(
                    review.get("supports_abstention"), bool
                ):
                    raise ValueError(f"Missing-evidence review is malformed: {query_id}")
            expanded.append({"query_id": query_id, "config": config,
                             "answerable": trace["answerable"], **review})
    result = {"split": "dev", "reviewed_questions": len(seen),
              "reviewed_contexts": len(expanded), "configs": {}}
    for config in ("C0", "C1"):
        subset = [row for row in expanded if row["config"] == config]
        answerable = [row for row in subset if row["answerable"]]
        missing = [row for row in subset if not row["answerable"]]
        counts = Counter(row["grade"] for row in answerable)
        score = sum(row["grade"] for row in answerable)
        result["configs"][config] = {
            "manual_quality": {
                "grade_0": counts[0], "grade_1": counts[1], "grade_2": counts[2],
                "mean_grade_of_2": statistics.mean(row["grade"] for row in answerable),
                "total_points": score, "possible_points": 2 * len(answerable),
                "full_evidence_and_citation": {"count": counts[2], "total": len(answerable)},
            },
            "missing_evidence_contexts_supporting_abstention": {
                "count": sum(row["supports_abstention"] for row in missing),
                "total": len(missing),
            },
            "review_status_counts": dict(Counter(row["needs_review_status"] for row in subset)),
        }
    return result


def main() -> None:
    trace_raw = (RUN / "traces.json").read_bytes()
    audit_raw = AUDIT.read_bytes()
    audit = json.loads(audit_raw.decode("utf-8-sig"))
    if hashlib.sha256(trace_raw).hexdigest() != audit["context_trace_sha256"]:
        raise RuntimeError("Manual audit does not match the frozen context trace")
    traces = json.loads(trace_raw.decode("utf-8-sig"))
    rows, _ = approved_rows()
    manual = summarize(audit, traces, rows)
    auto = json.loads((RUN / "metrics_auto.json").read_text(encoding="utf-8-sig"))
    if set(auto["configs"]) != set(manual["configs"]):
        raise RuntimeError("Auto and manual configurations differ")
    for config, result in manual["configs"].items():
        auto["configs"][config].update(result)
    auto["manual_audit_sha256"] = hashlib.sha256(audit_raw).hexdigest()
    auto["context_trace_sha256"] = audit["context_trace_sha256"]
    target = RUN / "metrics_reviewed.json"
    content = json.dumps(auto, ensure_ascii=False, indent=2) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") != content:
            raise FileExistsError(f"Different reviewed metrics will not be overwritten: {target}")
    else:
        target.write_text(content, encoding="utf-8")
    print(json.dumps({"metrics_reviewed": str(target), "manual": manual},
                     ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
