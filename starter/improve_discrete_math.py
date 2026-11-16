"""Build a reviewable Day 7 corpus v2 from the original PDFs, without indexing.

The v1 JSON is read for provenance and comparison only. This script never writes
chunks.json, the database, an embedding, or benchmark data.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import statistics
import sys
import tempfile
import unicodedata

from day6_integration import chapter_from_filename, slugify

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "discrete_math" / "raw"
V1 = ROOT / "starter" / "data" / "indexed" / "discrete_math" / "chunks.json"
V2 = V1.with_name("chunks_v2.json")
REPORT = ROOT / "report" / "individual" / "ingestion_v2_review.md"
MAX_TEXT = 620  # The Lab 07 context packer has an 800-character total budget.
STRUCTURE_START = re.compile(
    r"(?im)^(?=\s*(?:Bài\s+\d{1,3}\s*[.:]|Định nghĩa\s*[.:]|Định lý\s*[.:]|"
    r"Hệ quả\s*[.:]|Bổ đề\s*[.:]|Ví dụ\s*[.:]|VD\s*[.:]))"
)
FOOTER_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\s+Đại\s+Số\s+Boole\s+Trang\s+\d+\b", re.I)
PAGE_FOOTER = re.compile(r"^(?:Trang\s+)?\d{1,3}$", re.I)
PUA = re.compile(r"[\ue000-\uf8ff]")
FOOTER_DATE_CORE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\s+Đại\s+Số\s+Boole\b", re.I)
HEADER_ONLY = {
    "quan he thu tu", "qui tac suy dien", "chuong 2. cay",
    "chuong 2. cac bai toan ve duong di", "cau truc roi rac",
}


def fold(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().casefold()


def is_noise(text: str) -> bool:
    """Conservative removal: empty, page/footer, or isolated figure labels."""
    text = text.strip()
    if not text or PAGE_FOOTER.fullmatch(text):
        return True
    basic = fold(re.sub(r"(?m)^\s*(?:Trang\s+)?\d{1,3}\s*$", "", text)).strip()
    basic = re.sub(r"\s+", " ", basic)
    if basic in HEADER_ONLY:
        return True
    if len(text) < 160 and any(phrase in basic for phrase in ("bai thuyet trinh", "chan thanh cam on")):
        return True
    if len(text) < 100 and basic.startswith("logo"):
        return True
    if len(text) < 100 and "isaac newton" in basic:
        return True
    if len(text) < 100 and all(term in basic for term in ("phep hop", "phep giao", "phep hieu")):
        return True
    if len(text) < 110 and text.count("+") >= 8:
        return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(text) < 110 and len(lines) >= 6 and sum(len(line) == 1 for line in lines) / len(lines) > 0.6:
        return True
    if re.fullmatch(r"[\d\s.,:;|+\-]+", basic):
        return True
    if basic in {"logo", "het", "giai", "cam on", "cau truc roi rac"}:
        return True
    words = re.findall(r"[a-z]+", basic)
    if len(text) < 85 and len(words) >= 3 and all(len(word) <= 2 for word in words):
        return True
    return False


def credible_truth_table(rows: list[list[str]], page_text: str) -> bool:
    """Accept binary tables only when all cells, columns and rows are intact."""
    if "bang chan tri" not in fold(page_text) and "bang gia tri" not in fold(page_text):
        return False
    if len(rows) < 5 or len(rows) > 65:
        return False
    width = len(rows[0])
    if not 2 <= width <= 12 or any(len(row) != width for row in rows):
        return False
    if any(not cell.strip() for row in rows for cell in row):
        return False
    values = rows[1:]
    if len(values) & (len(values) - 1):  # truth tables have 2^n input rows
        return False
    return all(cell.strip() in {"0", "1"} for row in values for cell in row)


def markdown_table(rows: list[list[str]]) -> str:
    cleaned = [[cell.strip().replace("|", "\\|").replace("\n", " ") for cell in row] for row in rows]
    lines = ["| " + " | ".join(cleaned[0]) + " |", "| " + " | ".join("---" for _ in cleaned[0]) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in cleaned[1:])
    return "\n".join(lines)


def source_pages() -> list[dict]:
    """Read physical pages one at a time so citations retain the source page."""
    import viparse
    from pypdf import PdfReader, PdfWriter

    pdfs = sorted(RAW.glob("*.pdf"), key=lambda path: path.name.casefold())
    if not pdfs:
        raise FileNotFoundError(f"No PDFs in {RAW}")
    pages = []
    for path in pdfs:
        reader = PdfReader(path, strict=False)
        source_id = slugify(path.stem)
        source = (Path("data") / "discrete_math" / "raw" / path.name).as_posix()
        with tempfile.TemporaryDirectory(prefix="lab07-v2-page-") as temp_dir:
            for number, pdf_page in enumerate(reader.pages, start=1):
                writer = PdfWriter()
                writer.add_page(pdf_page)
                one_page = Path(temp_dir) / f"page-{number:04d}.pdf"
                with one_page.open("wb") as stream:
                    writer.write(stream)
                docs = viparse.load(one_page, output="json")
                if len(docs) != 1:
                    raise ValueError(f"Expected one extracted document for {path.name} page {number}")
                document = json.loads(docs[0].text)
                pages.append({
                    "source_id": source_id,
                    "source": source,
                    "page": number,
                    "chapter": chapter_from_filename(path.stem),
                    "blocks": document.get("blocks", []),
                    "encoding": document.get("encoding_detected"),
                    "encoding_confidence": document.get("encoding_confidence"),
                })
    return pages


def repeated_margins(pages: list[dict]) -> dict[str, set[str]]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for page in pages:
        lines = []
        for block in page["blocks"]:
            if block.get("type") == "paragraph":
                lines.extend(line.strip() for line in block.get("text", "").splitlines() if line.strip())
        candidates = set(lines[:2] + lines[-2:])
        counts[page["source_id"]].update(line for line in candidates if 2 < len(line) < 85)
    return {source: {line for line, n in count.items() if n >= 3} for source, count in counts.items()}


def clean_prose(text: str, page: dict, margins: set[str]) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r", "\n")
    text = FOOTER_DATE.sub("", text)
    text = FOOTER_DATE_CORE.sub("", text)
    text = re.sub(rf"\bTrang\s+{page['page']}\b", "", text, flags=re.I)
    # Verified on the rendered Chương 1 truth table, page 16.
    if page["source_id"] == "chuong-1-co-so-logic":
        text = text.replace("\uf0da", "∨").replace("\uf0ae", "→")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    cleaned = []
    for index, line in enumerate(lines):
        if not line:
            continue
        near_margin = index < 2 or index >= len(lines) - 2
        if near_margin and line in margins:
            continue
        if near_margin and PAGE_FOOTER.fullmatch(line) and (line == str(page["page"]) or line.lower().startswith("trang ")):
            continue
        if line.casefold() in {"logo", "hết"}:
            continue
        if line == "\uf06c":
            continue
        if page["source_id"] == "chuong-4-dai-so-boole":
            line = re.sub(r"^\uf0d8\s*", "- ", line)
        line = re.sub(r"^[\uf075\uf06e]\s*", "- ", line)
        line = re.sub(r"^\uf06c\s*", "- ", line)
        cleaned.append(line)
    # Slide themes sometimes draw a title as one glyph per line. Keep prose.
    result, vertical_run = [], []
    for line in cleaned:
        if len(line) == 1 and line.isalpha():
            vertical_run.append(line)
        else:
            if len(vertical_run) < 4:
                result.extend(vertical_run)
            vertical_run = []
            result.append(line)
    if len(vertical_run) < 4:
        result.extend(vertical_run)
    return "\n".join(result).strip()


def page_content(page: dict, margins: set[str]) -> tuple[str, list[str], bool]:
    raw_page_text = "\n".join(
        block.get("text", "") if block.get("type") == "paragraph" else " ".join(
            str(cell or "") for row in block.get("rows", []) for cell in row
        ) for block in page["blocks"]
    )
    parts, reasons = [], []
    valid_table = False
    for block in page["blocks"]:
        if block.get("type") == "paragraph":
            text = clean_prose(block.get("text", ""), page, margins)
            if text and not is_noise(text):
                parts.append(text)
        elif block.get("type") == "table":
            rows = [[str(cell or "").strip() for cell in row] for row in block.get("rows", [])]
            if credible_truth_table(rows, raw_page_text):
                # The font map for these two symbols was visually checked on page 16.
                if page["source_id"] == "chuong-1-co-so-logic":
                    rows = [[cell.replace("\uf0da", "∨").replace("\uf0ae", "→") for cell in row] for row in rows]
                parts.append(markdown_table(rows))
                valid_table = True
            else:
                cells = [cell for row in rows for cell in row if cell]
                if not cells:
                    continue  # decorative empty table detected by PDF parser
                fallback = clean_prose("\n".join(cells), page, margins)
                if fallback and not is_noise(fallback):
                    parts.append(fallback)
                    # A one-cell slide wrapper is prose; a multirow broken grid needs review.
                    if len(rows) > 1 and len(rows[0]) > 1:
                        reasons.append("table_columns_unreliable")
        else:
            text = clean_prose(str(block.get("text", "")), page, margins)
            if text and not is_noise(text):
                parts.append(text)
    text = "\n\n".join(parts).strip()
    if "\ufffd" in text:
        reasons.append("replacement_character")
    if PUA.search(text):
        reasons.append("unmapped_formula_symbol")
    if any(0x1D400 <= ord(char) <= 0x1D7FF for char in text) or any(char in text for char in "ഥҧ"):
        reasons.append("math_layout_requires_visual_check")
    folded = fold(text)
    if "ma tran" in folded:
        reasons.append("matrix_requires_visual_check")
    if ("bang chan tri" in folded or "bang gia tri" in folded) and not valid_table:
        reasons.append("table_not_verified")
    if any(cue in folded for cue in ("do thi sau", "cac do thi", "hinh ve", "hinh sau", "so do")):
        reasons.append("diagram_requires_visual_check")
    if page["source_id"] == "bai-tap-chuong-5" and text:
        reasons.append("graph_exercise_requires_visual_check")
    if page["source_id"] == "chuong-4-dai-so-boole" and "cong" in folded and ("chuyen doi" in folded or "xor" in folded):
        reasons.append("logic_gate_diagram_requires_visual_check")
    if page["source_id"] == "chuong-6-cay" and 12 <= page["page"] <= 14:
        reasons.append("tree_diagram_requires_visual_check")
    if len(text) < 120 and (fold(text).endswith(("hoi:", "sau day:", "sau:")) or text.rstrip().endswith(":") or ("suy luan" in folded and text.rstrip().endswith("?"))):
        reasons.append("incomplete_prompt")
    return text, sorted(set(reasons)), valid_table


def diagram_only_page(text: str, page: dict) -> bool:
    """Drop graph slides that provide a title/prompt but no usable evidence."""
    if page["source_id"] not in {"chuong-5-do-thi-phan-1", "chuong-5-do-thi-phan-2"}:
        return False
    folded = fold(text)
    if len(text) >= 110 or not any(term in folded for term in ("vi du", "dinh ly", "ma tran", "dieu kien du")):
        return False
    return not any(term in folded for term in ("khi va chi khi", "neu va chi neu", "la do thi", "co so dinh", "co so canh"))


def split_long(unit: str) -> list[str]:
    if len(unit) <= MAX_TEXT:
        return [unit]
    # Preserve paragraph, line and sentence boundaries before falling back to words.
    parts = re.split(r"\n\n+|(?<=[.!?;])\s+(?=[A-ZÀ-ỸĐ])|\n", unit)
    result, current = [], ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) > MAX_TEXT:
            if current:
                result.append(current)
                current = ""
            words = part.split()
            for word in words:
                candidate = f"{current} {word}".strip()
                if len(candidate) > MAX_TEXT and current:
                    result.append(current)
                    current = word
                else:
                    current = candidate
            continue
        candidate = f"{current}\n{part}".strip() if current else part
        if len(candidate) > MAX_TEXT:
            result.append(current)
            current = part
        else:
            current = candidate
    if current:
        result.append(current)
    return result


def segment(text: str) -> tuple[list[str], bool]:
    """Group complete semantic units within a page and the context budget."""
    units = [part.strip() for part in STRUCTURE_START.split(text) if part.strip()]
    if len(units) > 1 and len(units[0]) < 150 and not STRUCTURE_START.match(units[0]):
        units[1] = units[0] + "\n" + units[1]
        units.pop(0)
    pieces, forced = [], False
    for unit in units:
        split = split_long(unit)
        forced |= len(split) > 1
        pieces.extend(split)
    grouped, current = [], ""
    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if current and len(candidate) > MAX_TEXT:
            grouped.append(current)
            current = piece
        else:
            current = candidate
    if current:
        grouped.append(current)
    if len(grouped) > 1 and len(grouped[-1]) < 100 and len(grouped[-2]) + len(grouped[-1]) + 2 <= MAX_TEXT:
        grouped[-2] += "\n\n" + grouped.pop()
    return grouped, forced


def content_type(text: str, has_truth_table: bool) -> str:
    folded = fold(text)
    if has_truth_table and "| --- |" in text:
        return "truth_table"
    if re.search(r"(?im)^\s*Bài\s+\d+\s*[.:]", text):
        return "exercise"
    if "dinh nghia" in folded:
        return "definition"
    if "dinh ly" in folded or "he qua" in folded:
        return "theorem"
    if "vi du" in folded or re.search(r"(?im)^\s*VD\s*:", text):
        return "example"
    if "ma tran" in folded:
        return "matrix"
    return "explanation"


def build_v2(pages: list[dict], v1: list[dict]) -> tuple[list[dict], dict]:
    by_page: dict[tuple[str, int], list[str]] = defaultdict(list)
    for row in v1:
        by_page[(row["source_id"], row["page"])].append(row["id"])
    margins = repeated_margins(pages)
    output, removed, table_pages = [], [], []
    for page in pages:
        key = (page["source_id"], page["page"])
        text, reasons, has_table = page_content(page, margins.get(page["source_id"], set()))
        if is_noise(text) or diagram_only_page(text, page):
            removed.append(key)
            continue
        chunks, forced = segment(text)
        if forced:
            reasons.append("long_semantic_unit_split")
        if has_table:
            table_pages.append(key)
        for number, chunk in enumerate(chunks, start=1):
            if is_noise(chunk):
                continue
            if len(chunk) < 100 and chunk[:1].islower() and "long_semantic_unit_split" in reasons:
                continue  # orphaned tail from a broken formula/slide layout
            quality = "needs_review" if reasons else "ok"
            output.append({
                "id": f"{page['source_id']}:p{page['page']}:c{number}:v2",
                "text": chunk,
                "source_id": page["source_id"],
                "source": page["source"],
                "page": page["page"],
                "metadata": {
                    "subject": "discrete_math",
                    "chapter": page["chapter"],
                    "content_type": content_type(chunk, has_table),
                    "extraction_quality": quality,
                    "quality_reasons": sorted(set(reasons)),
                    "ingestion_version": "v2",
                    "encoding_detected": page["encoding"],
                    "encoding_confidence": page["encoding_confidence"],
                    "v1_chunk_ids": by_page.get(key, []),
                },
            })
    return output, {"removed_pages": removed, "truth_table_pages": table_pages, "physical_pages": len(pages)}


def measures(rows: list[dict]) -> dict:
    lengths = [len(row["text"]) for row in rows]
    return {
        "chunks": len(rows),
        "min_chars": min(lengths) if lengths else 0,
        "median_chars": statistics.median(lengths) if lengths else 0,
        "mean_chars": round(statistics.mean(lengths), 1) if lengths else 0,
        "max_chars": max(lengths) if lengths else 0,
        "under_100": sum(length < 100 for length in lengths),
        "page_only": sum(bool(PAGE_FOOTER.fullmatch(row["text"].strip())) for row in rows),
        "noise_proxy": sum(is_noise(row["text"]) for row in rows),
        "pua_proxy": sum(bool(PUA.search(row["text"])) for row in rows),
        "over_620": sum(length > MAX_TEXT for length in lengths),
    }


def compatibility_check(rows: list[dict]) -> dict:
    """Exercise lexical/schema adapters only; never invoke embeddings or SQL."""
    from baseline import TfidfIndex, pack_context

    lexical = TfidfIndex(rows)
    hits = lexical.search("đồ thị", top_k=3)
    context, context_ids = pack_context(hits, budget=800)
    candidates = sorted((ROOT.parent.parent / "lab06").glob("K5--Day06-*-DataIngestionEngineering"))
    if len(candidates) != 1:
        raise FileNotFoundError("Expected exactly one sibling Day06 repo for Chunk schema check")
    model_file = candidates[0] / "starter" / "src" / "models.py"
    spec = importlib.util.spec_from_file_location("day6_models_for_v2_audit", model_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load Day06 model contract: {model_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    day6_chunks = [module.Chunk(chunk_id=row["id"], document_id=row["source_id"],
                                source=row["source"], page=row["page"], text=row["text"],
                                metadata=row["metadata"]) for row in rows]
    block_lengths = [len(f"[{row['id']} | {row['source']} | page {row['page']}]\n{row['text']}") for row in rows]
    python_files = [path for path in list((ROOT / "starter").glob("*.py")) + list((ROOT / "src").glob("*.py"))
                    if path.resolve() != Path(__file__).resolve()]
    hybrid_found = any(re.search(r"\b(?:hybrid|rrf|reciprocal_rank_fusion)\b", path.read_text(encoding="utf-8"), re.I)
                       for path in python_files)
    return {
        "tfidf_indexed_rows": len(lexical.chunks),
        "tfidf_top3_count": len(hits),
        "tfidf_context_chunks": len(context_ids),
        "tfidf_context_chars": len(context),
        "day6_chunk_rows": len(day6_chunks),
        "single_chunk_fits_budget_800": sum(length <= 800 for length in block_lengths),
        "hybrid_implementation_found": hybrid_found,
    }


EXAMPLES = [
    ("Trang bìa/header", "chuong-1-co-so-logic", 1),
    ("Số trang đơn lẻ", "chuong-1-co-so-logic", 39),
    ("Số trang đơn lẻ", "chuong-1-co-so-logic", 45),
    ("Header lặp", "chuong-3-quan-he", 25),
    ("Footer ngày và số trang", "chuong-4-dai-so-boole", 4),
    ("Header lặp", "chuong-5-do-thi-phan-2", 33),
    ("Bảng chân trị có cấu trúc", "chuong-1-co-so-logic", 16),
    ("Bảng chân trị lệch cột", "chuong-4-dai-so-boole", 19),
    ("Bảng ở dạng hình", "chuong-4-dai-so-boole", 73),
    ("Ma trận dạng hình", "chuong-3-quan-he", 8),
    ("Hình đồ thị", "bai-tap-chuong-5", 1),
    ("Bài tập ma trận", "bai-tap-chuong-5", 2),
    ("Bài tập cây/ma trận", "bai-tap-chuong-6", 2),
    ("Bài tập nhiều ý", "bai-tap-chuong-5", 5),
    ("Công thức", "chuong-2-phep-dem", 54),
]


def report_text(v1: list[dict], v2: list[dict], info: dict, v1_sha: str, compat: dict) -> str:
    m1, m2 = measures(v1), measures(v2)
    flagged = sum(row["metadata"]["extraction_quality"] == "needs_review" for row in v2)
    by1: dict[tuple[str, int], list[dict]] = defaultdict(list)
    by2: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in v1:
        by1[(row["source_id"], row["page"])].append(row)
    for row in v2:
        by2[(row["source_id"], row["page"])].append(row)
    lines = [
        "# Audit ingestion Cấu trúc rời rạc: v1 → v2",
        "",
        "Đây là audit tại thời điểm tạo v2, trước khi index. Sau khi người dùng duyệt, v2 đã được index riêng; xem [báo cáo index và smoke retrieval](v2_index_smoke.md). Lệnh tạo v2 không embedding, ghi database, chạy benchmark hay thay dữ liệu chính thức.",
        f"SHA-256 của `chunks.json` v1: `{v1_sha}`.",
        "",
        "## Phạm vi nguồn",
        "",
        f"- Đã đọc {len(set(row['source_id'] for row in v2))} PDF, {info['physical_pages']} trang vật lý.",
        "- Trong `data/discrete_math/raw/` chỉ có 9 PDF; không có PPT/PPTX Chương 3. Vì vậy chưa thể xác nhận bộ 10 file gốc hay so sánh bản PDF/PPT Chương 3.",
        "- Quyền chia sẻ PDF và các trích đoạn trong báo cáo chưa được xác minh; cần kiểm tra trước khi công bố hoặc đưa báo cáo lên remote.",
        "- `source_id`, `source` và `page` là ID nguồn, đường dẫn và số trang vật lý của PDF hiện có. Trang chỉ chứa header/số trang có thể không có chunk v2.",
        "",
        "## So sánh định lượng",
        "",
        "| Chỉ số | v1 | v2 |",
        "|---|---:|---:|",
    ]
    labels = [("chunks", "Số chunks"), ("min_chars", "Độ dài nhỏ nhất"), ("median_chars", "Trung vị ký tự"),
              ("mean_chars", "Trung bình ký tự"), ("max_chars", "Độ dài lớn nhất"),
              ("under_100", "Chunks <100 ký tự"), ("page_only", "Chunks chỉ số trang"),
              ("noise_proxy", "Chunks vô nghĩa theo quy tắc"), ("pua_proxy", "Chunks chứa ký tự font toán chưa giải mã"),
              ("over_620", "Chunks >620 ký tự")]
    lines.extend(f"| {label} | {m1[key]} | {m2[key]} |" for key, label in labels)
    per_source_v1 = Counter(row["source_id"] for row in v1)
    per_source_v2 = Counter(row["source_id"] for row in v2)
    lines.extend([
        "",
        f"Tỷ lệ chunk vô nghĩa theo quy tắc: **{m1['noise_proxy']/len(v1):.1%}** ở v1 và **{m2['noise_proxy']/len(v2):.1%}** ở v2.",
        f"Tỷ lệ chunk cần người kiểm tra ở v2: **{flagged}/{len(v2)} = {flagged/len(v2):.1%}**; đây là cờ rủi ro trích xuất, không phải tỷ lệ sai được chấm thủ công.",
        f"Số trang không tạo chunk sau lọc: **{len(info['removed_pages'])}**. Bảng chân trị có hàng/cột hợp lệ: **{len(info['truth_table_pages'])}** trang.",
        "",
        "### Theo tài liệu",
        "",
        "| source_id | v1 | v2 | needs_review (v2) |",
        "|---|---:|---:|---:|",
    ])
    lines.extend(
        f"| `{source}` | {per_source_v1[source]} | {per_source_v2[source]} | "
        f"{sum(row['source_id'] == source and row['metadata']['extraction_quality'] == 'needs_review' for row in v2)} |"
        for source in sorted(per_source_v1)
    )
    lines.extend([
        "",
        "## Quy tắc v2 và giới hạn",
        "",
        "- Loại số trang, header/footer lặp, bảng rỗng do PDF parser tạo và đoạn chỉ có nhãn hình. Giữ số trang vật lý ở trường `page`.",
        "- Ưu tiên giữ trọn bài tập, định nghĩa, định lý, ví dụ và bảng trong một chunk. Mức 620 ký tự cho text dành chỗ cho citation header trong context budget 800 ký tự của Lab07; đơn vị dài hơn chỉ chia tại ranh giới dòng/câu, có cờ `long_semantic_unit_split`.",
        "- Bảng chân trị chỉ chuyển Markdown khi hàng/cột đầy đủ, không có ô trống, các hàng nhị phân và số hàng là lũy thừa của 2. Bảng lệch cột được giữ dưới dạng text gốc và gắn `needs_review`.",
        "- Ma trận, công thức font tùy biến và hình đồ thị không được suy đoán từ chuỗi nhãn/trọng số. Các chunk liên quan gắn `needs_review` và `quality_reasons`.",
        "- Các trang hình có thể chứa evidence không hiện diện trong text; cần đối chiếu PDF trước khi dùng làm câu trả lời có dẫn nguồn. Lỗi dấu tiếng Việt còn có thể tồn tại sau giải mã VNI.",
        "",
        "## Tương thích retrieval",
        "",
        "- `chunks_v2.json` giữ đúng 6 trường của schema Day07: `id`, `text`, `source_id`, `source`, `page`, `metadata`. ID có hậu tố `:v2` và duy nhất.",
        f"- TF-IDF: tạo chỉ mục trong bộ nhớ cho **{compat['tfidf_indexed_rows']}** hàng; truy vấn khói trả **{compat['tfidf_top3_count']}** hit, pack context được **{compat['tfidf_context_chunks']}** chunk / {compat['tfidf_context_chars']} ký tự. Không dùng benchmark để tính điểm.",
        f"- Context budget: **{compat['single_chunk_fits_budget_800']}/{len(v2)}** chunk riêng lẻ vừa 800 ký tự kể cả citation header. Bộ packer vẫn có thể bỏ hit nếu tổng nhiều chunk vượt ngân sách.",
        f"- Dense: **{compat['day6_chunk_rows']}** hàng ánh xạ được sang `src.models.Chunk` Day06. Audit này chỉ kiểm tra schema; truy vấn Dense thật sau khi index được ghi ở [báo cáo index và smoke retrieval](v2_index_smoke.md).",
        "- Hybrid: " + ("đã tìm thấy mã hybrid; chưa chạy end-to-end trong audit này." if compat["hybrid_implementation_found"] else "chưa có triển khai hybrid trong Python của repo để chạy end-to-end. Các hàng có ID/text/metadata chung cho fusion sau này."),
        "",
        "## 15 ví dụ trước/sau",
        "",
    ])
    for number, (label, source_id, page) in enumerate(EXAMPLES, start=1):
        before, after = by1[(source_id, page)], by2[(source_id, page)]
        old_text = "\n\n".join(row["text"] for row in before)
        new_text = "\n\n".join(row["text"] for row in after)
        old_preview = old_text[:450] + ("…" if len(old_text) > 450 else "")
        new_preview = new_text[:600] + ("…" if len(new_text) > 600 else "")
        quality = sorted({row["metadata"]["extraction_quality"] for row in after})
        reasons = sorted({reason for row in after for reason in row["metadata"]["quality_reasons"]})
        lines.extend([
            f"### {number}. {label}: `{source_id}` trang {page}",
            "",
            f"v1: {len(before)} chunk (`{', '.join(row['id'] for row in before) or 'không có'}`). v2: {len(after)} chunk (`{', '.join(row['id'] for row in after) or 'đã loại'}`).",
            f"Chất lượng v2: `{', '.join(quality) or 'không áp dụng'}`; lý do: `{', '.join(reasons) or 'không có'}`.",
            "",
            "Trước:", "", "```text", old_preview or "(không có)", "```", "",
            "Sau:", "", "```text", new_preview or "(đã loại khỏi v2)", "```", "",
        ])
    return "\n".join(lines)


def validate_output(v1: list[dict], v2: list[dict], pages: list[dict]) -> None:
    if not v2:
        raise ValueError("v2 has no chunks")
    ids = [row["id"] for row in v2]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate v2 chunk IDs")
    source_pages = {(page["source_id"], page["page"]): page for page in pages}
    allowed_keys = {"id", "text", "source_id", "source", "page", "metadata"}
    for row in v2:
        if set(row) != allowed_keys or not row["text"].strip():
            raise ValueError(f"Bad schema or empty text: {row.get('id')}")
        if is_noise(row["text"]):
            raise ValueError(f"Noise remained: {row['id']}")
        source = source_pages.get((row["source_id"], row["page"]))
        if source is None or row["source"] != source["source"]:
            raise ValueError(f"Bad source/page: {row['id']}")
        if any(key not in row["metadata"] for key in ("subject", "chapter", "content_type", "extraction_quality")):
            raise ValueError(f"Missing v2 metadata: {row['id']}")
    if {row["source_id"] for row in v2} != {row["source_id"] for row in v1}:
        raise ValueError("v2 source coverage differs from v1")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1", type=Path, default=V1)
    parser.add_argument("--output", type=Path, default=V2)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    if args.output.resolve() == args.v1.resolve():
        raise ValueError("Refusing to overwrite v1 chunks.json")
    v1_bytes = args.v1.read_bytes()
    v1_hash = hashlib.sha256(v1_bytes).hexdigest()
    v1 = json.loads(v1_bytes.decode("utf-8-sig"))
    pages = source_pages()
    v2, info = build_v2(pages, v1)
    validate_output(v1, v2, pages)
    compat = compatibility_check(v2)
    if hashlib.sha256(args.v1.read_bytes()).hexdigest() != v1_hash:
        raise RuntimeError("v1 changed during v2 generation")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(v2, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(report_text(v1, v2, info, v1_hash, compat), encoding="utf-8")
    print(json.dumps({"v1_sha256": v1_hash, "v1": measures(v1), "v2": measures(v2),
                      "needs_review": sum(row["metadata"]["extraction_quality"] == "needs_review" for row in v2),
                      "compatibility": compat, "output": str(args.output), "report": str(args.report)}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
