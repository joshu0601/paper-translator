"""Layout-preserving output (SPEC §62 page rendering, §20 figures stay in place).

* `render_page` rasterises a page of any PDF to PNG.
* `build_translated_pdf` produces a copy of the original PDF in which every
  translated paragraph is typeset *in its own bounding box*: the English text is
  redacted, the Traditional Chinese text is inserted with automatic font
  fallback and shrink-to-fit. Figures, tables, equations, headings, references
  and page decorations are untouched, so the translated PDF looks exactly like
  the original.
"""

from __future__ import annotations

import html
import logging
import re
from functools import lru_cache

import pymupdf

from app.models import Paragraph

log = logging.getLogger(__name__)

TRANSLATABLE_KINDS = {"paragraph", "list", "caption"}
_SPLIT_PUNCT = "。；！？.;!?"
_SOFT_PUNCT = "，、,"


def render_page(pdf_bytes: bytes, page_no: int, dpi: int = 120) -> bytes:
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        if not 1 <= page_no <= doc.page_count:
            raise ValueError("page out of range")
        pix = doc[page_no - 1].get_pixmap(dpi=dpi, alpha=False)
        return pix.tobytes("png")


def page_sizes(pdf_bytes: bytes) -> list[tuple[float, float]]:
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        return [(p.rect.width, p.rect.height) for p in doc]


def split_translation(text: str, ratios: list[float]) -> list[str]:
    """Split a translated paragraph into len(ratios) pieces whose lengths follow
    `ratios`, cutting at the nearest sentence/clause boundary."""
    if len(ratios) <= 1:
        return [text]
    total = sum(ratios) or 1.0
    pieces: list[str] = []
    rest = text
    for r in ratios[:-1]:
        if not rest:
            pieces.append("")
            continue
        target = int(len(rest) * (r / total))
        total -= r
        cut = _nearest_boundary(rest, target)
        pieces.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    pieces.append(rest)
    return pieces


def _nearest_boundary(text: str, target: int) -> int:
    if target <= 0:
        return 0
    if target >= len(text):
        return len(text)
    window = max(12, len(text) // 6)
    lo, hi = max(1, target - window), min(len(text) - 1, target + window)
    best, best_d = None, None
    for punct_set in (_SPLIT_PUNCT, _SOFT_PUNCT, " "):
        for i in range(lo, hi):
            if text[i - 1] in punct_set:
                d = abs(i - target)
                if best_d is None or d < best_d:
                    best, best_d = i, d
        if best is not None:
            return best
    return target


_MATH_CHARS = "∈∉∑∏∫≤≥≠≈∀∃→←∞∂∇⊆⊂∪∩|{}^"


def _math_fragment(text: str, boxes: list[dict]) -> bool:
    """Lines of prose broken up by display/inline math come out as tiny
    single-line fragments full of symbols. Re-typesetting those makes a mess,
    so they are left in English (equations themselves are never touched)."""
    words = text.split()
    if not words:
        return True
    single = sum(1 for w in words if len(w.strip(".,;:()")) <= 1)
    mathy = sum(text.count(c) for c in _MATH_CHARS)
    single_line = all(b.get("height", 0) < 1.9 * max(float(b.get("fontSize") or 9), 1) for b in boxes)
    if single_line and len(text) < 90 and (single or mathy):
        return True
    return single / len(words) >= 0.3 or mathy >= max(4, len(words) // 3)


def _boxes_by_page(paragraphs: list[Paragraph]) -> dict[int, list[tuple[pymupdf.Rect, str, float]]]:
    """page -> [(rect, translated text piece, font size)]"""
    out: dict[int, list[tuple[pymupdf.Rect, str, float]]] = {}
    for p in paragraphs:
        if p.kind not in TRANSLATABLE_KINDS or not p.translated_text or not p.boxes:
            continue
        if p.kind != "caption" and _math_fragment(p.original_text, p.boxes):
            continue
        boxes = [b for b in p.boxes if b.get("width", 0) > 4 and b.get("height", 0) > 4]
        if not boxes:
            continue
        pieces = split_translation(p.translated_text, [max(1, int(b.get("chars", 1))) for b in boxes])
        for b, piece in zip(boxes, pieces):
            if not piece.strip():
                continue
            rect = pymupdf.Rect(b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"])
            out.setdefault(int(b["page"]), []).append((rect, piece, float(b.get("fontSize") or 9.0)))
    return out


def _clean_for_pdf(text: str) -> str:
    # Strip the offline-mode marker and LaTeX delimiters that only the web reader renders.
    text = text.replace("〔模擬翻譯〕", "")
    text = re.sub(r"\$\$?([^$]+)\$\$?", r"\1", text)
    return text.strip()


def _page_lines(page: pymupdf.Page) -> list[pymupdf.Rect]:
    rects: list[pymupdf.Rect] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            if "".join(s.get("text", "") for s in line.get("spans", [])).strip():
                rects.append(pymupdf.Rect(line["bbox"]))
    return rects


def _has_partial_lines(rect: pymupdf.Rect, lines: list[pymupdf.Rect]) -> bool:
    """True when some text line straddles the rect border (partly in, partly out)."""
    for lr in lines:
        inter = rect & lr
        if inter.is_empty:
            continue
        area = lr.get_area()
        if area <= 0:
            continue
        frac = inter.get_area() / area
        if 0.08 < frac < 0.7:
            return True
    return False


def _drop_overlapping(items: list[tuple[pymupdf.Rect, str, float]]) -> list[tuple[pymupdf.Rect, str, float]]:
    """Two replacement boxes overlapping each other would print on top of each
    other; keep the larger one and leave the smaller in the original language."""
    keep: list[tuple[pymupdf.Rect, str, float]] = []
    for it in sorted(items, key=lambda it: -it[0].get_area()):
        rect = it[0]
        clash = False
        for other in keep:
            inter = rect & other[0]
            if not inter.is_empty and inter.get_area() > 0.2 * min(rect.get_area(), other[0].get_area()):
                clash = True
                break
        if not clash:
            keep.append(it)
    return keep


def _css(size: float) -> str:
    return (
        f"* {{ font-family: sans-serif; font-size: {size:.2f}pt; line-height: 1.32; "
        "margin: 0; padding: 0; text-align: justify; color: #111; }"
    )


def _fits(body: str, rect: pymupdf.Rect, size: float) -> bool:
    story = pymupdf.Story(html=body, user_css=_css(size))
    more, _ = story.place(rect)
    return not more


def _fit_font_size(body: str, rect: pymupdf.Rect, base: float) -> float:
    """Chinese is denser than English, so the translation at the original size
    often fills only part of the box. Grow it a little (max 1.2x) when it still
    fits; shrinking below the base size is left to insert_htmlbox's scaling."""
    for factor in (1.2, 1.12, 1.06):
        if _fits(body, rect, base * factor):
            return base * factor
    return base


def build_translated_pdf(pdf_bytes: bytes, paragraphs: list[Paragraph]) -> bytes:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    per_page = _boxes_by_page(paragraphs)
    for page_no, items in per_page.items():
        if page_no < 1 or page_no > doc.page_count:
            continue
        page = doc[page_no - 1]
        # Only replace boxes that cleanly contain their text: a box that cuts
        # through a foreign line (an equation fragment, a table row) would leave
        # half-redacted glyphs and overlapping text behind.
        lines = _page_lines(page)
        items = [it for it in items if not _has_partial_lines(it[0], lines)]
        items = _drop_overlapping(items)
        # 1) remove the English text of every translated block (keep images & drawings)
        for rect, _, _ in items:
            page.add_redact_annot(rect + (-0.5, -0.5, 0.5, 0.5))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        # 2) typeset the Chinese text into the same rectangles
        for rect, piece, font_size in items:
            body = f"<div>{html.escape(_clean_for_pdf(piece))}</div>"
            size = _fit_font_size(body, rect, font_size)
            try:
                page.insert_htmlbox(rect, body, css=_css(size), scale_low=0.45)
            except Exception as exc:  # pragma: no cover - never let one block break the PDF
                log.warning("insert_htmlbox failed on page %s: %s", page_no, exc)
    out = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return out


@lru_cache(maxsize=64)
def cached_page_sizes(document_id: str, storage_key: str) -> list[tuple[float, float]]:
    from app.services.storage import get_storage

    return page_sizes(get_storage().get(storage_key))
