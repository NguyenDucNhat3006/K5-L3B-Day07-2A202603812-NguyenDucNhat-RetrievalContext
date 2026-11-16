"""Read-only Dense, TF-IDF and RRF retrieval over the approved Day 07 V2 corpus."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import time
from typing import Any

from baseline import TfidfIndex
from day6_integration import Day6DenseRetriever
from index_discrete_math import EXPECTED_MODEL, discover_day6_root, load_day6_modules
from index_discrete_math_v2 import (
    EXPECTED_DIMENSIONS,
    STRATEGY,
    checked_inputs,
    index_ready_rows,
    stored_rows,
    verify_stored,
)


def approved_rows() -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Read V2 and derive exactly the metadata stored in pgvector, without writing."""
    source_rows, hashes = checked_inputs()
    return index_ready_rows(source_rows, hashes["v2_sha256"]), hashes


def _valid_request(query: str, filters: dict[str, Any] | None, top_k: int) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if filters is None:
        return {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be a JSON object")
    normalized = {}
    for key, value in filters.items():
        if not isinstance(key, str) or not key or value is None or value == "":
            raise ValueError("filter keys and values must be non-empty")
        if key == "source_id":
            key = "document_id"
        if key in normalized and normalized[key] != value:
            raise ValueError("conflicting source_id/document_id filters")
        normalized[key] = value
    return normalized


def _jsonb_contains(actual: Any, expected: Any) -> bool:
    """Match PostgreSQL JSONB containment for the metadata values used here."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _jsonb_contains(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and all(
            any(_jsonb_contains(item, wanted) for item in actual) for wanted in expected
        )
    return type(actual) is type(expected) and actual == expected


def _matches(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, value in filters.items():
        if key == "document_id":
            actual = row["source_id"]
        elif key in ("source", "page"):
            actual = row[key]
        else:
            actual = row["metadata"].get(key)
        if not _jsonb_contains(actual, value):
            return False
    return True


def _result(row: dict[str, Any], score: float, rank: int, strategy: str,
            **extra: Any) -> dict[str, Any]:
    if not math.isfinite(float(score)):
        raise ValueError("retrieval score must be finite")
    return {**row, "chunk_id": row["id"], "score": float(score), "rank": rank,
            "strategy": strategy, **extra}


class V2RetrievalSuite:
    """All methods share canonical rows and their exact V2 metadata."""

    def __init__(self, rows: list[dict[str, Any]], dense_backend: Any) -> None:
        self.rows = rows
        self.by_id = {row["id"]: row for row in rows}
        if not rows or len(self.by_id) != len(rows):
            raise ValueError("V2 corpus must be non-empty and have unique IDs")
        started = time.perf_counter()
        self.lexical = TfidfIndex(rows)
        self.tfidf_build_seconds = time.perf_counter() - started
        self.dense_backend = dense_backend

    def dense(self, query: str, *, filters: dict[str, Any] | None = None,
              top_k: int = 3) -> list[dict[str, Any]]:
        normalized = _valid_request(query, filters, top_k)
        raw = self.dense_backend.search(query, filters=normalized, top_k=top_k)
        results = []
        for rank, hit in enumerate(raw, start=1):
            chunk_id = hit.get("id", hit.get("chunk_id"))
            row = self.by_id.get(chunk_id)
            if row is None:
                raise RuntimeError(f"Dense returned a chunk outside approved V2: {chunk_id}")
            if (hit.get("text"), hit.get("source"), hit.get("page")) != (
                row["text"], row["source"], row["page"]
            ):
                raise RuntimeError(f"Dense citation/text differs from approved V2: {chunk_id}")
            if not _matches(row, normalized):
                raise RuntimeError(f"Dense backend violated metadata filter: {chunk_id}")
            results.append(_result(row, hit["score"], rank, "dense"))
        return results

    def tfidf(self, query: str, *, filters: dict[str, Any] | None = None,
              top_k: int = 3) -> list[dict[str, Any]]:
        normalized = _valid_request(query, filters, top_k)
        # Search all 332 first so filtering preserves the unfiltered TF-IDF weights.
        ranked = self.lexical.search(query, top_k=len(self.rows))
        selected = (hit for hit in ranked if _matches(hit, normalized))
        results = []
        for hit in selected:
            results.append(_result(self.by_id[hit["id"]], hit["score"],
                                   len(results) + 1, "tfidf"))
            if len(results) == top_k:
                break
        return results

    def hybrid(self, query: str, *, filters: dict[str, Any] | None = None,
               top_k: int = 3, candidate_k: int = 20,
               rrf_k: int = 60) -> list[dict[str, Any]]:
        normalized = _valid_request(query, filters, top_k)
        if not isinstance(candidate_k, int) or candidate_k < 1 or not isinstance(rrf_k, int) or rrf_k < 1:
            raise ValueError("candidate_k and rrf_k must be positive integers")
        depth = max(top_k, candidate_k)
        dense = self.dense(query, filters=normalized, top_k=depth)
        lexical = self.tfidf(query, filters=normalized, top_k=depth)
        fused: dict[str, dict[str, Any]] = {}
        for name, hits in (("dense", dense), ("tfidf", lexical)):
            for hit in hits:
                item = fused.setdefault(hit["id"], {"score": 0.0, "dense_rank": None,
                                                     "tfidf_rank": None})
                item["score"] += 1.0 / (rrf_k + hit["rank"])
                item[f"{name}_rank"] = hit["rank"]
        ordered = sorted(fused, key=lambda chunk_id: (
            -fused[chunk_id]["score"],
            min(rank for rank in (fused[chunk_id]["dense_rank"], fused[chunk_id]["tfidf_rank"])
                if rank is not None),
            chunk_id,
        ))
        return [_result(self.by_id[chunk_id], fused[chunk_id]["score"], rank,
                        "hybrid_rrf", dense_rank=fused[chunk_id]["dense_rank"],
                        tfidf_rank=fused[chunk_id]["tfidf_rank"])
                for rank, chunk_id in enumerate(ordered[:top_k], start=1)]

    def search(self, strategy: str, query: str, *, filters: dict[str, Any] | None = None,
               top_k: int = 3, candidate_k: int = 20, rrf_k: int = 60) -> list[dict[str, Any]]:
        if strategy == "dense":
            return self.dense(query, filters=filters, top_k=top_k)
        if strategy == "tfidf":
            return self.tfidf(query, filters=filters, top_k=top_k)
        if strategy == "hybrid_rrf":
            return self.hybrid(query, filters=filters, top_k=top_k,
                               candidate_k=candidate_k, rrf_k=rrf_k)
        raise ValueError(f"Unknown retrieval strategy: {strategy}")


def live_suite() -> tuple[V2RetrievalSuite, Any, dict[str, str], float]:
    """Load the existing model/index and verify all 332 DB rows; SELECT only."""
    rows, hashes = approved_rows()
    started = time.perf_counter()
    _, _, MyEmbedder, PgVectorStore = load_day6_modules(discover_day6_root())
    model_name = os.getenv("EMBEDDING_MODEL") or EXPECTED_MODEL
    if model_name != EXPECTED_MODEL:
        raise RuntimeError(f"Day06 model differs from approved V2 index: {model_name}")
    embedder = MyEmbedder(model_name)
    if embedder.dimensions != EXPECTED_DIMENSIONS:
        raise RuntimeError("Day06 embedding dimension differs from V2 index")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from Day06 starter/.env")
    store = PgVectorStore(database_url, EXPECTED_DIMENSIONS)
    verify_stored(rows, stored_rows(store))
    elapsed = time.perf_counter() - started
    return V2RetrievalSuite(rows, Day6DenseRetriever(embedder, store, STRATEGY)), store, hashes, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Day07 V2 retrieval")
    parser.add_argument("--strategy", choices=("dense", "tfidf", "hybrid_rrf"), required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--filters", default="{}", help="JSON object; no gold-derived filters")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    filters = json.loads(args.filters)
    suite, _, _, _ = live_suite()
    # ASCII JSON survives Windows cp1252 consoles and PowerShell pipes unchanged.
    print(json.dumps(suite.search(args.strategy, args.query, filters=filters,
                                  top_k=args.top_k), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
