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
    metadata: dict = field(default_factory=dict)


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


def _block_from_dict(page_no: int, raw: dict) -> Block | None:
    lines: list[str] = []
    size_weighted = 0.0
    bold_chars = 0
    chars = 0
    for line in raw.get("lines", []):
        spans = line.get("spans", [])
        text = "".join(s.get("text", "") for s in spans)
        if not text.strip():
            continue
        lines.append(text)
        for s in spans:
            n = len(s.get("text", ""))
            if n == 0:
                continue
            chars += n
            size_weighted += s.get("size", 0.0) * n
            if s.get("flags", 0) & 16 or "bold" in s.get("font", "").lower():
                bold_chars += n
    text = _join_lines(lines)
    if not text or chars == 0:
        return None
    x0, y0, x1, y1 = raw["bbox"]
    return Block(
        page=page_no,
        bbox=(x0, y0, x1, y1),
        text=text,
        font_size=round(size_weighted / chars, 2),
        bold_ratio=bold_chars / chars,
        char_count=chars,
    )


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


def _merge_adjacent(blocks: list[Block]) -> list[Block]:
    """Merge consecutive blocks that are really lines of the same paragraph.

    PyMuPDF sometimes emits one block per line. Two blocks are joined when they
    sit in the same column, use the same font size, are separated by less than
    one line of whitespace, and the second one is not indented (an indent marks
    a new paragraph in most academic templates)."""
    merged: list[Block] = []
    for b in blocks:
        if merged:
            prev = merged[-1]
            gap = b.bbox[1] - prev.bbox[3]
            same_font = abs(prev.font_size - b.font_size) <= 0.6
            same_col = prev.column == b.column and prev.page == b.page
            indent = b.bbox[0] - prev.bbox[0]
            # Lines inside a paragraph are ~0.1–0.4 em apart; paragraph spacing is larger.
            close = -prev.font_size * 0.5 <= gap <= prev.font_size * 0.55
            not_new_para = indent <= prev.font_size * 0.8
            # A single short line followed by a full-width line ends a paragraph.
            prev_single_line = (prev.bbox[3] - prev.bbox[1]) < prev.font_size * 1.8
            prev_ends_short = prev_single_line and (prev.bbox[2] - prev.bbox[0]) < 0.7 * max(b.bbox[2] - b.bbox[0], 1)
            bold_mismatch = (prev.bold_ratio >= 0.6) != (b.bold_ratio >= 0.6)
            if (
                same_font and same_col and close and not_new_para and not prev_ends_short
                and not bold_mismatch and not _CAPTION_START.match(b.text)
                and not _REF_START.match(b.text)
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
    for page_idx, page in enumerate(doc):
        page_no = page_idx + 1
        width, height = page.rect.width, page.rect.height
        result.page_sizes.append((width, height))

        raw = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_MEDIABOX_CLIP)
        page_blocks: list[Block] = []
        for rb in raw.get("blocks", []):
            if rb.get("type") != 0:
                continue
            b = _block_from_dict(page_no, rb)
            if b:
                page_blocks.append(b)
        result.blocks.extend(_merge_adjacent(_reading_order(page_blocks, width)))

        if extract_tables:
            try:
                tables = page.find_tables()
                for t in tables.tables:
                    rows = [[(c or "").strip() for c in row] for row in t.extract()]
                    rows = [r for r in rows if any(r)]
                    if len(rows) < 2:
                        continue
                    result.tables.append(TableBlock(page=page_no, bbox=tuple(t.bbox), rows=rows, index=table_index))
                    table_index += 1
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
