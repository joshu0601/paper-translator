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


_WORD_PUNCT = ".,;:()[]{}\"'“”‘’•"


def _real_words(text: str) -> int:
    return sum(1 for w in text.split() if len(w.strip(_WORD_PUNCT)) >= 3 and w.strip(_WORD_PUNCT).isalpha())


def _math_fragment(text: str) -> bool:
    """Display math broken into tiny pieces ("RT s", "i , p−", "= Eπ") has
    practically no words; re-typesetting it makes a mess, so it stays as is.
    Prose that merely contains some math is translated normally."""
    words = text.split()
    if not words:
        return True
    real = _real_words(text)
    if real < 3:
        return True
    return len(words) >= 8 and real / len(words) < 0.2


def _replaceable(p: Paragraph) -> bool:
    if p.kind not in TRANSLATABLE_KINDS or not p.translated_text or not p.boxes:
        return False
    return p.kind == "caption" or not _math_fragment(p.original_text)


def _rect(b: dict) -> pymupdf.Rect:
    return pymupdf.Rect(b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"])


def _coalesce_boxes(boxes: list[dict]) -> list[dict]:
    """Merge a paragraph's fragment boxes that sit in the same column and are
    vertically adjacent (lines broken around inline math) into one box, so the
    translation is typeset once per column segment instead of per fragment."""
    merged: list[dict] = []
    for b in boxes:
        if merged:
            m = merged[-1]
            fs = max(float(m.get("fontSize") or 9), 1.0)
            same_page = m["page"] == b["page"]
            x_overlap = min(m["x"] + m["width"], b["x"] + b["width"]) - max(m["x"], b["x"])
            narrow = min(m["width"], b["width"])
            gap = b["y"] - (m["y"] + m["height"])
            if same_page and x_overlap >= 0.5 * max(narrow, 1) and -1.5 * fs <= gap <= 1.5 * fs:
                x0, y0 = min(m["x"], b["x"]), min(m["y"], b["y"])
                x1 = max(m["x"] + m["width"], b["x"] + b["width"])
                y1 = max(m["y"] + m["height"], b["y"] + b["height"])
                c_m, c_b = max(int(m.get("chars", 0)), 1), max(int(b.get("chars", 0)), 1)
                size = (float(m.get("fontSize") or 9) * c_m + float(b.get("fontSize") or 9) * c_b) / (c_m + c_b)
                merged[-1] = {**m, "x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0,
                              "chars": c_m + c_b, "fontSize": round(size, 2)}
                continue
        merged.append(dict(b))
    return merged


def _boxes_by_page(paragraphs: list[Paragraph]) -> dict[int, list[tuple[pymupdf.Rect, str, float, str]]]:
    """page -> [(rect, translated text piece, font size, original paragraph text)]"""
    out: dict[int, list[tuple[pymupdf.Rect, str, float, str]]] = {}
    for p in paragraphs:
        if not _replaceable(p):
            continue
        boxes = _coalesce_boxes([b for b in p.boxes if b.get("width", 0) > 2 and b.get("height", 0) > 2])
        boxes = [b for b in boxes if b.get("width", 0) > 4 and b.get("height", 0) > 4]
        if not boxes:
            continue
        pieces = split_translation(p.translated_text, [max(1, int(b.get("chars", 1))) for b in boxes])
        for b, piece in zip(boxes, pieces):
            if not piece.strip():
                continue
            out.setdefault(int(b["page"]), []).append((_rect(b), piece, float(b.get("fontSize") or 9.0), p.original_text))
    return out


def _protected_by_page(paragraphs: list[Paragraph]) -> dict[int, list[pymupdf.Rect]]:
    """Boxes of text that must survive untouched: equations, references,
    math fragments, anything without a translation."""
    out: dict[int, list[pymupdf.Rect]] = {}
    for p in paragraphs:
        if _replaceable(p):
            continue
        for b in p.boxes or []:
            if b.get("width", 0) > 2 and b.get("height", 0) > 2:
                out.setdefault(int(b["page"]), []).append(_rect(b))
    return out


def _clean_for_pdf(text: str) -> str:
    # Strip the offline-mode marker and LaTeX delimiters that only the web reader renders.
    text = text.replace("〔模擬翻譯〕", "")
    text = re.sub(r"\$\$?([^$]+)\$\$?", r"\1", text)
    return text.strip()


def _page_lines(page: pymupdf.Page) -> list[tuple[pymupdf.Rect, str]]:
    lines: list[tuple[pymupdf.Rect, str]] = []
    # Same flags as the extractor (ligatures expanded) so texts compare equal.
    flags = pymupdf.TEXT_PRESERVE_WHITESPACE | pymupdf.TEXT_MEDIABOX_CLIP
    for block in page.get_text("dict", flags=flags)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
            if text:
                lines.append((pymupdf.Rect(line["bbox"]), text))
    return lines


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


_WORD_RE = re.compile(r"[A-Za-z]{4,}")


def _belongs(line_text: str, own_norm: str) -> bool:
    """Does this PDF line come from the paragraph?

    Word-based: most of the line's real words must occur in the paragraph.
    This survives hyphenated line ends, ligatures and inline math whose
    sub/superscripts live in separate PDF lines."""
    words = [w.lower() for w in _WORD_RE.findall(line_text)]
    if not words:
        key = _norm(line_text).rstrip("-–").lower()
        return not key or key[:14] in own_norm
    hits = sum(1 for w in words if w in own_norm)
    return hits >= max(1, round(0.6 * len(words)))


def _safe_boxes(
    rect: pymupdf.Rect,
    lines: list[tuple[pymupdf.Rect, str]],
    protected: list[pymupdf.Rect],
    font_size: float,
    own_text: str,
) -> list[pymupdf.Rect]:
    """Turn a paragraph box into the rectangles that may be redacted and
    re-typeset without damaging anything else.

    * Lines whose text belongs to the paragraph (including sub/superscript
      pieces poking out of the box) are absorbed so the English is removed
      cleanly.
    * A neighbouring column's line touching the side trims the box.
    * Everything else that overlaps the box - display equations, references,
      protected text, foreign fragments - carves it into the parts above and
      below, and the translation is spread over those parts.
    """
    box = pymupdf.Rect(rect)
    crossing: list[pymupdf.Rect] = []
    fs = max(font_size, 1.0)
    own = _norm(own_text).lower()

    def side_trim(lr: pymupdf.Rect) -> None:
        nonlocal box
        if lr.x0 > (rect.x0 + rect.x1) / 2:
            box.x1 = min(box.x1, lr.x0 - 1)
        else:
            box.x0 = max(box.x0, lr.x1 + 1)

    # Pass 1: the paragraph's own text lines (used to tell inline math pieces
    # from display equations) and side neighbours.
    own_lines: list[pymupdf.Rect] = []
    foreign: list[tuple[pymupdf.Rect, str]] = []
    for lr, text in lines:
        inter = rect & lr
        if inter.is_empty or lr.get_area() <= 0:
            continue
        frac = inter.get_area() / lr.get_area()
        if frac <= 0.08:
            continue  # barely touching: belongs to a neighbouring box
        cx = (lr.x0 + lr.x1) / 2
        if not rect.x0 <= cx <= rect.x1:
            side_trim(lr)
            continue
        # Text inside a protected box (an equation paragraph) is never ours,
        # even when its words also occur in the paragraph.
        in_protected = any((lr & pr).get_area() >= 0.5 * lr.get_area() for pr in protected)
        if not in_protected and len(_norm(text)) >= 4 and _belongs(text, own):
            own_lines.append(lr)
            if frac < 0.7:
                box |= lr  # our own line poking out (sub/superscript, descender)
        else:
            foreign.append((lr, text))

    def on_own_line(lr: pymupdf.Rect) -> bool:
        """Shares a line band with the paragraph's text (i.e. inline, not display)."""
        cy = (lr.y0 + lr.y1) / 2
        return any(o.y0 - 0.2 * fs <= cy <= o.y1 + 0.2 * fs for o in own_lines)

    # Pass 2: foreign pieces. Inline pieces (a subscript, "= 0", a symbol
    # sitting on one of our lines) are redacted with the line; anything on its
    # own line (display equation, other paragraph) carves the box.
    for lr in protected:
        inter = rect & lr
        if inter.is_empty:
            continue
        cx = (lr.x0 + lr.x1) / 2
        if not rect.x0 <= cx <= rect.x1:
            side_trim(lr)
        elif on_own_line(lr) and lr.width <= 0.6 * max(rect.width, 1):
            box |= lr
        else:
            crossing.append(lr)
    for lr, text in foreign:
        if on_own_line(lr) and lr.width <= 0.6 * max(rect.width, 1):
            box |= lr
        else:
            crossing.append(lr)

    pieces: list[pymupdf.Rect] = []
    y = box.y0
    for lr in sorted(crossing, key=lambda r: r.y0):
        top = min(lr.y0, box.y1) - 0.5
        if top - y >= 1.2 * fs:
            pieces.append(pymupdf.Rect(box.x0, y, box.x1, top))
        y = max(y, lr.y1 + 0.5)
    if box.y1 - y >= 1.2 * fs:
        pieces.append(pymupdf.Rect(box.x0, y, box.x1, box.y1))
    return [p for p in pieces if p.width >= 20]


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
    protected_by_page = _protected_by_page(paragraphs)
    for page_no, items in per_page.items():
        if page_no < 1 or page_no > doc.page_count:
            continue
        page = doc[page_no - 1]
        # Shape every box so that redacting it cannot damage foreign text
        # (equations, neighbouring lines); a box crossing an equation is split
        # into the parts above and below it and the translation is spread over
        # them.
        lines = _page_lines(page)
        protected = protected_by_page.get(page_no, [])
        shaped: list[tuple[pymupdf.Rect, str, float]] = []
        for rect, piece, font_size, own_text in items:
            parts = _safe_boxes(rect, lines, protected, font_size, own_text)
            if not parts:
                continue
            if len(parts) == 1:
                shaped.append((parts[0], piece, font_size))
                continue
            for part, sub in zip(parts, split_translation(piece, [p.height for p in parts])):
                if sub.strip():
                    shaped.append((part, sub, font_size))
        items = _drop_overlapping(shaped)
        # 1) remove the English text of every translated block (keep images & drawings)
        for rect, *_ in items:
            page.add_redact_annot(rect + (-0.5, 0, 0.5, 0))
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
