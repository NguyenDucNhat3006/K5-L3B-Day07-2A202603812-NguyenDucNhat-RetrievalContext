"""Chunk Day 7 PDFs and index them in the existing Day 6 pgvector database.

Run with the Day 6 virtual environment so the exact same embedding model and
database adapter are used. Existing Day 6 A/B rows are untouched; the Day 7
corpus is isolated by strategy name ``D07_discrete_math``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

from day6_integration import chapter_from_filename, slugify, to_day7_chunk

REPO_ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = REPO_ROOT / "data" / "discrete_math" / "raw"
OUTPUT_DIR = REPO_ROOT / "starter" / "data" / "indexed" / "discrete_math"
STRATEGY = "D07_discrete_math"
EXPECTED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 500


def discover_day6_root(explicit: Path | None = None) -> Path:
    """Resolve Day 6 repo from --day6-root, DAY6_ROOT, or sibling workspace."""
    configured = explicit or (Path(os.environ["DAY6_ROOT"]) if os.getenv("DAY6_ROOT") else None)
    if configured:
        root = configured.expanduser().resolve()
        if not (root / "starter" / "src" / "run.py").is_file():
            raise FileNotFoundError(f"Not a Day 6 repository: {root}")
        return root

    lab_dir = Path(__file__).resolve().parents[3]
    matches = sorted((lab_dir / "lab06").glob("K5--Day06-*-DataIngestionEngineering"))
    valid = [p for p in matches if (p / "starter" / "src" / "run.py").is_file()]
    if len(valid) != 1:
        raise RuntimeError("Set DAY6_ROOT or pass --day6-root to the Day 6 repository")
    return valid[0]


def load_day6_modules(day6_root: Path):
    """Import Day 6 chunk/embed/store code and add VNI-aware page extraction."""
    day6_starter = str(day6_root / "starter")
    if day6_starter not in sys.path:
        sys.path.insert(0, day6_starter)
    from dotenv import load_dotenv

    load_dotenv(day6_root / "starter" / ".env")
    from src.chunking import by_paragraph
    from src.embeddings import MyEmbedder
    from src.ingestion import normalize_text
    from src.models import DocumentPage
    from src.store import PgVectorStore

    def load_pdf(path: Path, document_id: str, source: str):
        """Extract each page separately and decode legacy Vietnamese fonts."""
        import viparse
        from pypdf import PdfReader, PdfWriter

        pages = []
        with tempfile.TemporaryDirectory(prefix="day07-pdf-pages-") as temp_dir:
            reader = PdfReader(path, strict=False)
            page_paths = []
            for page_number, pdf_page in enumerate(reader.pages, start=1):
                writer = PdfWriter()
                writer.add_page(pdf_page)
                page_path = Path(temp_dir) / f"page-{page_number:04d}.pdf"
                with page_path.open("wb") as stream:
                    writer.write(stream)
                page_paths.append((page_number, page_path))

            for page_number, page_path in page_paths:
                docs = viparse.load(page_path, output="text")
                if len(docs) != 1:
                    raise ValueError(f"Expected one extracted document for {path.name} page {page_number}")
                doc = docs[0]
                confidence = doc.metadata.encoding_confidence
                text = normalize_text(doc.text)
                if "\ufffd" in text:
                    raise ValueError(f"Replacement character found in {path.name} page {page_number}")
                pages.append(
                    DocumentPage(
                        document_id=document_id,
                        source=source,
                        page=page_number,
                        text=text,
                        metadata={
                            "empty_page": not bool(text),
                            "file_name": path.name,
                            "text_encoding_detected": doc.metadata.encoding_detected,
                            "text_encoding_confidence": confidence,
                            "text_encoding_low_confidence": confidence is not None and confidence < 0.75,
                            "pdf_extractor": "viparse",
                        },
                    )
                )
        return pages

    return load_pdf, by_paragraph, MyEmbedder, PgVectorStore


def build_chunks(load_pdf, by_paragraph) -> tuple[list[Any], list[dict[str, Any]], list[str], dict[str, Any]]:
    """Extract PDF text, paragraph-chunk per page, and produce Day 7 JSON rows."""
    pdfs = sorted(PDF_DIR.glob("*.pdf"), key=lambda p: p.name.casefold())
    if not pdfs:
        raise FileNotFoundError(f"No PDFs found in {PDF_DIR}")

    chunks, output_rows, document_ids = [], [], []
    source_stats = []
    for pdf_path in pdfs:
        source_id = slugify(pdf_path.stem)
        if source_id in document_ids:
            raise ValueError(f"Filename collision creates duplicate source_id: {source_id}")
        document_ids.append(source_id)
        source = (Path("data") / "discrete_math" / "raw" / pdf_path.name).as_posix()
        pages = load_pdf(pdf_path, document_id=source_id, source=source)
        content_page_count = 0
        before = len(chunks)
        chapter = chapter_from_filename(pdf_path.stem)
        for page in pages:
            if not page.text.strip():
                continue
            content_page_count += 1
            page.metadata.update(
                {
                    "file_name": pdf_path.name,
                    "source_path": source,
                    "document_title": pdf_path.stem,
                    "chunking_method": "paragraph",
                    "max_chars": CHUNK_SIZE,
                }
            )
            if chapter is not None:
                page.metadata["chapter"] = chapter
            page_chunks = by_paragraph(page, max_size=CHUNK_SIZE)
            for index, chunk in enumerate(page_chunks, start=1):
                # Both the stored ID and exported ID use the Day 7 contract.
                chunk.chunk_id = f"{source_id}:p{page.page}:c{index}"
                chunk.metadata.update(
                    {
                        "file_name": pdf_path.name,
                        "source_path": source,
                        "document_title": pdf_path.stem,
                        "chunking_method": "paragraph",
                        "max_chars": CHUNK_SIZE,
                    }
                )
                if chapter is not None:
                    chunk.metadata["chapter"] = chapter
                chunks.append(chunk)
                output_rows.append(to_day7_chunk(chunk, source_id, source, index))
        source_stats.append(
            {
                "source_id": source_id,
                "source": source,
                "physical_pages": len(pages),
                "content_pages": content_page_count,
                "chunks": len(chunks) - before,
            }
        )
    if not chunks:
        raise ValueError("PDF extraction/chunking produced no text chunks")
    ids = [row["id"] for row in output_rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Chunk IDs are not unique")
    stats = {
        "pdf_count": len(pdfs),
        "physical_pages": sum(row["physical_pages"] for row in source_stats),
        "content_pages": sum(row["content_pages"] for row in source_stats),
        "chunk_count": len(chunks),
        "chunk_size_chars": CHUNK_SIZE,
        "chunking_method": "paragraph, page-bounded",
        "sources": source_stats,
    }
    return chunks, output_rows, document_ids, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day6-root", type=Path, help="Day 6 repository (defaults to the sibling lab06 folder)")
    parser.add_argument("--prepare-only", action="store_true", help="Write schema-compliant chunks JSON without embedding or DB writes")
    args = parser.parse_args()

    day6_root = discover_day6_root(args.day6_root)
    load_pdf, by_paragraph, MyEmbedder, PgVectorStore = load_day6_modules(day6_root)
    chunks, rows, document_ids, stats = build_chunks(load_pdf, by_paragraph)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chunk_path = OUTPUT_DIR / "chunks.json"
    chunk_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.prepare_only:
        print(json.dumps({**stats, "chunks_json": str(chunk_path), "index_status": "not indexed"}, ensure_ascii=True, indent=2))
        return

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL missing in Day 6 starter/.env")
    model_name = os.getenv("EMBEDDING_MODEL") or EXPECTED_MODEL
    if model_name != EXPECTED_MODEL:
        raise ValueError(f"Expected the Day 6 model {EXPECTED_MODEL!r}, got {model_name!r}")

    embedder = MyEmbedder(model_name)
    if embedder.dimensions != 384:
        raise ValueError(f"Expected 384-dimensional Day 6 vectors; got {embedder.dimensions}")
    store = PgVectorStore(database_url, dimensions=embedder.dimensions)
    existing_day6 = {
        name: store.count_chunks(name) for name in ("A_fixed", "B_paragraph")
    }
    if any(count == 0 for count in existing_day6.values()):
        raise RuntimeError(f"Expected populated Day 6 A/B indexes before adding Day 7 data; found {existing_day6}")

    started = time.perf_counter()
    vectors = embedder.embed_documents([chunk.text for chunk in chunks])
    embedding_seconds = time.perf_counter() - started
    if len(vectors) != len(chunks):
        raise RuntimeError(f"Embedding returned {len(vectors)} vectors for {len(chunks)} chunks")

    store.upsert(STRATEGY, chunks, vectors, document_ids=document_ids)
    indexed_count = store.count_chunks(STRATEGY)
    if indexed_count != len(chunks):
        raise RuntimeError(f"Post-upsert count mismatch: expected {len(chunks)}, found {indexed_count}")

    index_info = {
        **stats,
        "embedding_model": model_name,
        "embedding_dimensions": embedder.dimensions,
        "vector_store": "Day 6 PostgreSQL + pgvector",
        "strategy": STRATEGY,
        "day6_index_counts_before": existing_day6,
        "day7_index_count_after": indexed_count,
        "embedding_seconds": round(embedding_seconds, 3),
        "chunks_json": str(chunk_path),
        "vector_values_in_json": False,
    }
    (OUTPUT_DIR / "index_info.json").write_text(
        json.dumps(index_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(index_info, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
