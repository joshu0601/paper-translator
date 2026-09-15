"""PDF text / image / table extraction with PyMuPDF (SPEC §7, §62).

The extractor is deliberately "dumb": it returns layout blocks with font
statistics in reading order. All interpretation (headings, paragraphs,
captions...) happens in `app.services.parsing.structure`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pymupdf


@dataclass
class Block:
    page: int  # 1-based
    bbox: tuple[float, float, float, float]
    text: str
    font_size: float
    bold_ratio: float
    char_count: int
    column: int = 0  # 0 = left / full width, 1 = right column
    para_start: bool = False  # known paragraph start (first line indented) - never merge into previous


@dataclass
class ImageBlock:
    page: int
    bbox: tuple[float, float, float, float]
    png: bytes
    index: int


@dataclass
class TableBlock:
    page: int
    bbox: tuple[float, float, float, float]
    rows: list[list[str]]
    index: int


@dataclass
class ExtractedDocument:
    page_count: int
    page_sizes: list[tuple[float, float]]
    blocks: list[Block] = field(default_factory=list)
    images: list[ImageBlock] = field(default_factory=list)
    tables: list[TableBlock] = field(default_factory=list)
    # Areas covered by ruled tables (page, bbox) - text inside is not prose.
    table_regions: list[tuple[int, tuple[float, float, float, float]]] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def _merge_table_regions(rects: list[tuple[float, float, float, float]]) -> list[tuple[float, float, float, float]]:
    """`find_tables` often returns one degenerate 1-row "table" per band between
    two horizontal rules. Bands that share the same horizontal extent and sit
    close to each other belong to one table; their union is the table area."""
    regions: list[list[float]] = []
    for r in sorted(rects, key=lambda r: (r[1], r[0])):
        x0, y0, x1, y1 = r
        for reg in regions:
            overlap = min(x1, reg[2]) - max(x0, reg[0])
            narrow = min(x1 - x0, reg[2] - reg[0])
            if overlap >= 0.8 * max(narrow, 1.0) and y0 - reg[3] <= 40 and y1 >= reg[1] - 40:
                reg[0], reg[1], reg[2], reg[3] = min(reg[0], x0), min(reg[1], y0), max(reg[2], x1), max(reg[3], y1)
                break
        else:
            regions.append([x0, y0, x1, y1])
    return [tuple(r) for r in regions]  # type: ignore[return-value]


_HYPHEN_END = re.compile(r"(\w)-$")


def _join_lines(lines: list[str]) -> str:
    """Join wrapped lines, undoing end-of-line hyphenation."""
    out = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not out:
            out = line
            continue
        if _HYPHEN_END.search(out) and line[:1].islower():
            out = out[:-1] + line
        else:
            out = f"{out} {line}"
    return re.sub(r"[ \t]+", " ", out).strip()


@dataclass
class _Line:
    text: str
    bbox: tuple[float, float, float, float]
    size_weighted: float
    bold_chars: int
    chars: int


def _lines_from_dict(raw: dict) -> list[_Line]:
    lines: list[_Line] = []
    for line in raw.get("lines", []):
        spans = line.get("spans", [])
        text = "".join(s.get("text", "") for s in spans)
        if not text.strip():
            continue
        size_weighted = 0.0
        bold = 0
        chars = 0
        for s in spans:
            n = len(s.get("text", ""))
            if n == 0:
                continue
            chars += n
            size_weighted += s.get("size", 0.0) * n
            if s.get("flags", 0) & 16 or "bold" in s.get("font", "").lower():
                bold += n
        if chars:
            lines.append(_Line(text, tuple(line["bbox"]), size_weighted, bold, chars))
    return lines


def _block_from_lines(page_no: int, lines: list[_Line]) -> Block | None:
    text = _join_lines([ln.text for ln in lines])
    chars = sum(ln.chars for ln in lines)
    if not text or chars == 0:
        return None
    x0 = min(ln.bbox[0] for ln in lines)
    y0 = min(ln.bbox[1] for ln in lines)
    x1 = max(ln.bbox[2] for ln in lines)
    y1 = max(ln.bbox[3] for ln in lines)
    return Block(
        page=page_no,
        bbox=(x0, y0, x1, y1),
        text=text,
        font_size=round(sum(ln.size_weighted for ln in lines) / chars, 2),
        bold_ratio=sum(ln.bold_chars for ln in lines) / chars,
        char_count=chars,
    )


_PARA_START = re.compile(r"^([A-Z(\[\"“•\-–]|\d+[\.)]\s)")


def _split_paragraphs(lines: list[_Line]) -> list[list[_Line]]:
    """Split a multi-line block into paragraphs.

    Many publisher templates (Elsevier, Springer...) separate paragraphs only
    by a first-line indent, so PyMuPDF returns a whole column as one block. A
    new paragraph starts at a line that is indented relative to the block's
    left edge, or that follows a short (non-justified) last line."""
    if len(lines) < 2:
        return [lines]
    # The body left edge is the most common line start (robust to hanging
    # indents of list items, where only the first line sits further left).
    from collections import Counter

    left = Counter(round(ln.bbox[0]) for ln in lines).most_common(1)[0][0]
    right = max(ln.bbox[2] for ln in lines)
    width = max(right - left, 1.0)
    size = max(sum(ln.size_weighted for ln in lines) / max(sum(ln.chars for ln in lines), 1), 1.0)
    # Only justified prose is split on a short last line; ragged blocks
    # (keyword lists, addresses, author lines) have many short lines.
    full_lines = sum(1 for ln in lines if (ln.bbox[2] - left) >= width * 0.9)
    justified = full_lines >= max(2, int(len(lines) * 0.6))

    groups: list[list[_Line]] = [[lines[0]]]
    for prev, cur in zip(lines, lines[1:]):
        indent = cur.bbox[0] - left
        prev_short = (prev.bbox[2] - left) < width * 0.8
        indented = size * 0.6 <= indent <= size * 4
        starts_new = bool(_PARA_START.match(cur.text.strip()))
        gap = cur.bbox[1] - prev.bbox[3]
        if (indented and starts_new) or (justified and prev_short and starts_new and gap > -size * 0.3):
            groups.append([cur])
        else:
            groups[-1].append(cur)
    return groups


def _first_line_indented(lines: list[_Line]) -> bool:
    if len(lines) < 2:
        return False
    rest_left = min(ln.bbox[0] for ln in lines[1:])
    size = max(sum(ln.size_weighted for ln in lines) / max(sum(ln.chars for ln in lines), 1), 1.0)
    return size * 0.6 <= lines[0].bbox[0] - rest_left <= size * 4


def _blocks_from_dict(page_no: int, raw: dict) -> list[Block]:
    lines = _lines_from_dict(raw)
    if not lines:
        return []
    out: list[Block] = []
    for i, group in enumerate(_split_paragraphs(lines)):
        b = _block_from_lines(page_no, group)
        if b:
            b.para_start = i > 0 or _first_line_indented(group)
            out.append(b)
    return out


def _reading_order(blocks: list[Block], page_width: float) -> list[Block]:
    """Order blocks for one page: full-width blocks split the page into bands;
    inside a band, left column first, then right column, each top-to-bottom."""
    if not blocks:
        return []
    mid = page_width / 2
    full_width_threshold = page_width * 0.6

    for b in blocks:
        width = b.bbox[2] - b.bbox[0]
        center = (b.bbox[0] + b.bbox[2]) / 2
        if width >= full_width_threshold:
            b.column = -1  # full width
        else:
            b.column = 0 if center < mid else 1

    by_y = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
    ordered: list[Block] = []
    band: list[Block] = []

    def flush() -> None:
        left = sorted((b for b in band if b.column == 0), key=lambda b: b.bbox[1])
        right = sorted((b for b in band if b.column == 1), key=lambda b: b.bbox[1])
        ordered.extend(left)
        ordered.extend(right)
        band.clear()

    for b in by_y:
        if b.column == -1:
            flush()
            ordered.append(b)
        else:
            band.append(b)
    flush()
    for b in ordered:
        if b.column == -1:
            b.column = 0
    return ordered


_CAPTION_START = re.compile(r"^(Fig\.?|Figure|Table|TABLE|FIGURE)\s*\d", re.I)
_REF_START = re.compile(r"^\[\d{1,3}\]\s")
_EQ_TAG = re.compile(r"\(\d{1,3}[a-z]?\)\s*$")
_WORD = re.compile(r"[A-Za-z]{4,}")


def _looks_math(text: str) -> bool:
    """A display-equation line: numbered tag at the end, or an '=' with hardly
    any words. Such lines are never merged into prose."""
    if _EQ_TAG.search(text) and len(text) < 200:
        return True
    return "=" in text and len(_WORD.findall(text)) < 3


def _typical_line_gap(raw_blocks: list[dict]) -> float | None:
    """Median vertical gap between consecutive lines inside multi-line blocks -
    the page's real line pitch (some layouts stretch it to fill the column)."""
    gaps: list[float] = []
    for rb in raw_blocks:
        if rb.get("type") != 0:
            continue
        lines = [ln for ln in rb.get("lines", []) if "".join(s.get("text", "") for s in ln.get("spans", [])).strip()]
        for a, b in zip(lines, lines[1:]):
            gap = b["bbox"][1] - a["bbox"][3]
            if -2 <= gap <= 20:
                gaps.append(gap)
    if len(gaps) < 3:
        return None
    gaps.sort()
    return gaps[len(gaps) // 2]


def _merge_adjacent(blocks: list[Block], line_gap: float | None = None) -> list[Block]:
    """Merge consecutive blocks that are really lines of the same paragraph.

    PyMuPDF sometimes emits one block per line. Two blocks are joined when they
    sit in the same column, use the same font size, are separated by less than
    one line of whitespace, and the second one is not indented (an indent marks
    a new paragraph in most academic templates)."""
    # Right edges shared by several lines are the justified column edges;
    # a line ending exactly there is a full line (ragged text never repeats
    # the same right edge that consistently).
    from collections import Counter

    justified_edges: set[int] = set()
    by_left: dict[int, list[Block]] = {}
    for b in blocks:
        by_left.setdefault(round(b.bbox[0] / 4), []).append(b)
    for group in by_left.values():
        counts = Counter(round(b.bbox[2]) for b in group)
        # Ragged text repeats a right edge only by chance; justified columns
        # share it on most lines.
        justified_edges.update(x for x, n in counts.items() if n >= max(3, 0.4 * len(group)))

    merged: list[Block] = []
    for b in blocks:
        if merged:
            prev = merged[-1]
            gap = b.bbox[1] - prev.bbox[3]
            same_font = abs(prev.font_size - b.font_size) <= 0.6
            same_col = prev.column == b.column and prev.page == b.page
            indent = b.bbox[0] - prev.bbox[0]
            # Lines inside a paragraph sit at the page's line pitch (typically
            # 0.1–0.4 em, more when a column is vertically justified);
            # paragraph spacing is noticeably larger than that.
            limit = prev.font_size * 0.55 if line_gap is None else max(prev.font_size * 0.55, line_gap + prev.font_size * 0.35)
            # A justified line that runs the full column width cannot be the
            # last line of a paragraph, so the next line continues it even when
            # the column's line pitch was stretched (vertical justification).
            prev_full = round(prev.bbox[2]) in justified_edges and abs(prev.bbox[0] - b.bbox[0]) <= prev.font_size * 1.5
            if prev_full:
                limit = max(limit, prev.font_size * 1.1)
            close = -prev.font_size * 0.5 <= gap <= limit
            not_new_para = indent <= prev.font_size * 0.8
            # A single short line followed by a full-width line ends a paragraph.
            prev_single_line = (prev.bbox[3] - prev.bbox[1]) < prev.font_size * 1.8
            prev_ends_short = prev_single_line and (prev.bbox[2] - prev.bbox[0]) < 0.7 * max(b.bbox[2] - b.bbox[0], 1)
            bold_mismatch = (prev.bold_ratio >= 0.6) != (b.bold_ratio >= 0.6)
            if (
                same_font and same_col and close and not_new_para and not prev_ends_short
                and not bold_mismatch and not b.para_start and not _CAPTION_START.match(b.text)
                and not _REF_START.match(b.text)
                and not _looks_math(b.text) and not _looks_math(prev.text)
            ):
                prev.text = _join_lines([prev.text, b.text])
                prev.bbox = (min(prev.bbox[0], b.bbox[0]), prev.bbox[1], max(prev.bbox[2], b.bbox[2]), b.bbox[3])
                total = prev.char_count + b.char_count
                prev.bold_ratio = (prev.bold_ratio * prev.char_count + b.bold_ratio * b.char_count) / max(total, 1)
                prev.font_size = round((prev.font_size * prev.char_count + b.font_size * b.char_count) / max(total, 1), 2)
                prev.char_count = total
                continue
        merged.append(b)
    return merged


def extract(pdf_bytes: bytes, *, extract_images: bool = True, extract_tables: bool = True) -> ExtractedDocument:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    result = ExtractedDocument(page_count=doc.page_count, page_sizes=[], metadata=dict(doc.metadata or {}))

    image_index = 0
    table_index = 0
    # Pass 1: text. Line pitch is measured per page, falling back to the
    # document-wide value on pages that carry only a few lines (figure pages).
    raw_pages = [page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_MEDIABOX_CLIP) for page in doc]
    doc_gap = _typical_line_gap([rb for raw in raw_pages for rb in raw.get("blocks", [])])

    for page_idx, page in enumerate(doc):
        page_no = page_idx + 1
        width, height = page.rect.width, page.rect.height
        result.page_sizes.append((width, height))

        raw = raw_pages[page_idx]
        page_blocks: list[Block] = []
        for rb in raw.get("blocks", []):
            if rb.get("type") != 0:
                continue
            page_blocks.extend(_blocks_from_dict(page_no, rb))
        line_gap = _typical_line_gap(raw.get("blocks", [])) or doc_gap
        result.blocks.extend(_merge_adjacent(_reading_order(page_blocks, width), line_gap))

        if extract_tables:
            try:
                tables = page.find_tables()
                rects: list[tuple[float, float, float, float]] = []
                for t in tables.tables:
                    rects.append(tuple(t.bbox))
                    rows = [[(c or "").strip() for c in row] for row in t.extract()]
                    rows = [r for r in rows if any(r)]
                    if len(rows) < 2:
                        continue
                    result.tables.append(TableBlock(page=page_no, bbox=tuple(t.bbox), rows=rows, index=table_index))
                    table_index += 1
                for region in _merge_table_regions(rects):
                    # A single thin band is a rule, not a table.
                    if region[3] - region[1] >= 20:
                        result.table_regions.append((page_no, region))
            except Exception:  # pragma: no cover - table detection is best effort
                pass

        if extract_images:
            seen: set[int] = set()
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in seen:
                    continue
                seen.add(xref)
                try:
                    rects = page.get_image_rects(xref)
                    if not rects:
                        continue
                    rect = rects[0]
                    # Skip tiny decorations / logos.
                    if rect.width < 60 or rect.height < 60:
                        continue
                    pix = pymupdf.Pixmap(doc, xref)
                    if pix.n - pix.alpha >= 4:  # CMYK -> RGB
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    png = pix.tobytes("png")
                    if len(png) < 2000:
                        continue
                    result.images.append(ImageBlock(page=page_no, bbox=(rect.x0, rect.y0, rect.x1, rect.y1), png=png, index=image_index))
                    image_index += 1
                except Exception:  # pragma: no cover
                    continue

    doc.close()
    return result


def page_count(pdf_bytes: bytes) -> int:
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        return doc.page_count
