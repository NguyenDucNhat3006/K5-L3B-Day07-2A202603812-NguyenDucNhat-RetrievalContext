"""Adapters for sharing the Day 6 embedding model and pgvector database."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def slugify(value: str) -> str:
    """Create a stable ASCII ID from a PDF filename stem."""
    value = value.replace("Đ", "D").replace("đ", "d")
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    if not value:
        raise ValueError("Cannot make a document ID from an empty filename")
    return value


def chunk_id(source_id: str, page: int, chunk_index: int) -> str:
    """Day 7 traceable ID: source_id:pN:cN (both numbers are 1-based)."""
    if not source_id or page < 1 or chunk_index < 1:
        raise ValueError("source_id must be set; page and chunk_index must be >= 1")
    return f"{source_id}:p{page}:c{chunk_index}"


def chapter_from_filename(filename: str) -> int | None:
    """Read a chapter number only when the source filename states one."""
    slug = slugify(filename)
    match = re.search(r"(?:bai-tap-)?chuong-(\d+)", slug)
    return int(match.group(1)) if match else None


def to_day7_chunk(chunk: Any, source_id: str, source: str, index_on_page: int) -> dict[str, Any]:
    """Convert a Day 6 Chunk into Day 7's JSON contract."""
    if not chunk.text or not chunk.text.strip():
        raise ValueError("Cannot export an empty chunk")
    metadata = dict(chunk.metadata)
    return {
        "id": chunk_id(source_id, chunk.page, index_on_page),
        "text": chunk.text,
        "source_id": source_id,
        "source": source,
        "page": chunk.page,
        "metadata": metadata,
    }


class Day6DenseRetriever:
    """Day 7 Retriever protocol backed by the Day 6 pgvector index."""

    def __init__(self, embedder: Any, store: Any, strategy: str) -> None:
        if not strategy:
            raise ValueError("strategy must not be empty")
        self.embedder = embedder
        self.store = store
        self.strategy = strategy

    def search(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Return Day 7 chunk-shaped results from the real pgvector store."""
        import math
        import numpy as np
        import psycopg

        if top_k <= 0:
            raise ValueError("top_k must be > 0")
        filters = filters or {}
        if not isinstance(filters, dict):
            raise ValueError("filters must be a mapping")
        vector = self.embedder.embed_query(query)
        if len(vector) != self.store.dimensions or not all(math.isfinite(float(v)) for v in vector):
            raise ValueError("Query embedding is invalid or has the wrong dimension")
        vector = np.asarray(vector, dtype=np.float32)
        conditions = ["strategy = %s"]
        params: list[Any] = [self.strategy]
        column_filters = {"document_id", "source", "page"}
        for key, value in filters.items():
            if value is None or value == "":
                raise ValueError(f"Filter {key!r} must have a value")
            if key in column_filters:
                conditions.append(f"{key} = %s")
                params.append(value)
            else:
                # JSONB containment accepts arbitrary metadata without SQL identifiers.
                conditions.append("metadata @> %s")
                params.append(psycopg.types.json.Jsonb({key: value}))
        where = " AND ".join(conditions)
        sql = f"""
            SELECT chunk_id, document_id, source, page, text, metadata,
                   1 - (embedding <=> %s) AS score
            FROM chunks
            WHERE {where}
            ORDER BY embedding <=> %s
            LIMIT %s
        """
        with self.store._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, [vector, *params, vector, top_k])
                rows = cur.fetchall()
        hits = [
            {
                "chunk_id": row[0],
                "text": row[4],
                "score": float(row[6]),
                "metadata": {
                    **(row[5] or {}),
                    "document_id": row[1],
                    "source": row[2],
                    "page": row[3],
                },
            }
            for row in rows
        ]
        results = []
        for hit in hits:
            metadata = dict(hit.get("metadata", {}))
            source_id = metadata.get("document_id")
            if not source_id:
                raise ValueError(f"Stored chunk {hit.get('chunk_id')} has no document_id")
            results.append(
                {
                    "id": hit["chunk_id"],
                    "text": hit["text"],
                    "source_id": source_id,
                    "source": metadata.get("source"),
                    "page": metadata.get("page"),
                    "metadata": metadata,
                    "score": hit["score"],
                }
            )
        return results
