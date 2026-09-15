"""Document structure detection (SPEC §8, §63).

Turns the flat block list from the PDF extractor into
Document metadata -> Sections -> Paragraphs / Figures / Tables.

Heading detection combines typography (font size / boldness relative to the
body text), numbering patterns and a semantic classifier over well-known
section names. Nothing here assumes a fixed template.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from app.services.pdf.extractor import Block, ExtractedDocument, ImageBlock, TableBlock

# --------------------------------------------------------------------------- #
# Data classes shared with the pipeline
# --------------------------------------------------------------------------- #


@dataclass
class ParsedParagraph:
    text: str
    page: int
    kind: str = "paragraph"  # paragraph | heading | equation | caption | list | reference
    bbox: tuple[float, float, float, float] | None = None


@dataclass
class ParsedSection:
    title: str
    kind: str
    number: str | None
    start_page: int
    paragraphs: list[ParsedParagraph] = field(default_factory=list)

    @property
    def end_page(self) -> int:
        return max((p.page for p in self.paragraphs), default=self.start_page)


@dataclass
class ParsedFigure:
    page: int
    caption: str
    label: str | None
    png: bytes
    section_index: int | None


@dataclass
class ParsedTable:
    page: int
    caption: str
    label: str | None
    rows: list[list[str]]
    section_index: int | None


@dataclass
class ParsedDocument:
    title: str
    authors: list[str]
    affiliations: list[str]
    abstract: str | None
    keywords: list[str]
    year: int | None
    doi: str | None
    venue: str | None
    sections: list[ParsedSection]
    figures: list[ParsedFigure]
    tables: list[ParsedTable]


# --------------------------------------------------------------------------- #
# Semantic section classification (SPEC §8)
# --------------------------------------------------------------------------- #

SECTION_KINDS: list[tuple[str, re.Pattern[str]]] = [
    ("abstract", re.compile(r"^abstract\b", re.I)),
    ("keywords", re.compile(r"^(keywords?|index terms)\b", re.I)),
    ("introduction", re.compile(r"^introduction\b", re.I)),
    ("related_work", re.compile(r"^(related work|literature review|prior work|previous work)\b", re.I)),
    ("background", re.compile(r"^(background|preliminar(y|ies)|motivation)\b", re.I)),
    ("system_model", re.compile(r"^(system model|network model|system architecture|system overview)\b", re.I)),
    ("problem_formulation", re.compile(r"^(problem (formulation|statement|definition)|optimization problem)\b", re.I)),
    ("algorithm", re.compile(r"^(algorithm|proposed (algorithm|scheme|solution|approach|framework)|solution approach)\b", re.I)),
    ("methodology", re.compile(r"^(method(ology|s)?|approach|proposed method|model|framework|design)\b", re.I)),
    ("experiment", re.compile(r"^(experiment(s|al)?( setup| settings| design)?|evaluation|simulation( setup| results)?|implementation)\b", re.I)),
    ("results", re.compile(r"^(results?|performance( evaluation| analysis)?|numerical results|findings)\b", re.I)),
    ("discussion", re.compile(r"^(discussion|analysis|limitations?)\b", re.I)),
    ("conclusion", re.compile(r"^(conclusions?|concluding remarks|summary( and future work)?|future work)\b", re.I)),
    ("acknowledgements", re.compile(r"^acknowledg", re.I)),
    ("references", re.compile(r"^(references|bibliography)\b", re.I)),
    ("appendix", re.compile(r"^appendi(x|ces)\b", re.I)),
]

_NUMBERED_HEADING = re.compile(
    r"^(?P<num>(?:\d+(?:\.\d+)*\.?|[IVXLC]+\.|[A-Z]\.))\s+(?P<title>[A-Z][^\n]{1,120})$"
)
_ROMAN = re.compile(r"^[IVXLC]+$")
_CAPTION = re.compile(r"^(?P<label>(Fig\.?|Figure|Table|TABLE|FIGURE)\s*(?P<num>\d+[a-z]?))[\.:\s]", re.I)
_EQUATION_TAG = re.compile(r"\(\s*\d+[a-z]?\s*\)\s*$")
_REFERENCE_ITEM = re.compile(r"^\[\d+\]|^\d+\.\s+[A-Z]")
_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+)", re.I)
_YEAR = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ARXIV = re.compile(r"arxiv:\s*\d{4}\.\d{4,5}", re.I)
_PAGE_NUMBER = re.compile(r"^\s*(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?\s*$", re.I)


def classify_section(title: str) -> str:
    t = title.strip()
    for kind, pattern in SECTION_KINDS:
        if pattern.search(t):
            return kind
    return "other"


def _roman_to_int(s: str) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = 0
    prev = 0
    for ch in reversed(s):
        v = vals.get(ch, 0)
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    return total


# --------------------------------------------------------------------------- #
# Heuristics
# --------------------------------------------------------------------------- #


def _body_font_size(blocks: list[Block]) -> float:
    counter: Counter[float] = Counter()
    for b in blocks:
        counter[round(b.font_size * 2) / 2] += b.char_count
    if not counter:
        return 10.0
    return counter.most_common(1)[0][0]


def _looks_like_heading(b: Block, body: float) -> tuple[bool, str | None, str]:
    """Return (is_heading, section_number, title)."""
    text = b.text.strip()
    if len(text) > 140 or len(text) < 3:
        return False, None, text
    if text.endswith((".", ",", ";")) and not _NUMBERED_HEADING.match(text):
        # Headings rarely end with punctuation ("1. Introduction." is unusual).
        if not re.match(r"^\d+(\.\d+)*\.\s*$", text):
            return False, None, text
    if _CAPTION.match(text):
        return False, None, text

    bigger = b.font_size >= body * 1.08
    bold = b.bold_ratio >= 0.6
    m = _NUMBERED_HEADING.match(text)
    if m:
        num = m.group("num").rstrip(".")
        title = m.group("title").strip()
        if _ROMAN.match(num):
            num = str(_roman_to_int(num))
        # Numbered + (bigger or bold) is a very strong signal; numbered alone is
        # accepted when the text is short.
        if bigger or bold or len(text) <= 60:
            return True, num, title
        return False, None, text

    kind = classify_section(text)
    if kind != "other" and (bigger or bold or text.isupper() or len(text.split()) <= 3):
        return True, None, text.title() if text.isupper() else text
    if (bigger and b.font_size >= body * 1.2 and len(text.split()) <= 12) or (
        bold and len(text.split()) <= 8 and not text.endswith(".")
    ):
        return True, None, text
    return False, None, text


def _is_noise(b: Block, body: float, page_height: float, repeated: set[str]) -> bool:
    text = b.text.strip()
    if _PAGE_NUMBER.match(text):
        return True
    if text in repeated:
        return True
    top = b.bbox[1] < page_height * 0.06
    bottom = b.bbox[3] > page_height * 0.94
    if (top or bottom) and (b.font_size < body * 0.9 or len(text) < 80):
        return True
    if b.font_size < body * 0.7 and len(text) < 40:
        return True
    if _ARXIV.search(text) and len(text) < 120:
        return True
    return False


def _is_equation(text: str) -> bool:
    if _EQUATION_TAG.search(text) and len(text) < 300:
        return True
    symbols = sum(text.count(c) for c in "=∑∫∏≤≥≈∈∀∃αβγδλμσθπ⋅×÷±√∞∂∇")
    letters = sum(c.isalpha() for c in text)
    return len(text) < 200 and symbols >= 2 and symbols * 6 > max(letters, 1)


def _should_merge(prev: str, nxt: str) -> bool:
    """Merge paragraph fragments split across columns / pages."""
    if not prev or not nxt:
        return False
    if prev.endswith(("-",)):
        return True
    if prev[-1] in ".!?:;\"”’)]}":
        return False
    first = nxt[:1]
    return first.islower() or first in "(,;" or prev[-1] in ",—–"


def _clean_title(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text.rstrip(" .*†‡")


def _split_authors(text: str) -> list[str]:
    text = _EMAIL.sub("", text)
    text = re.sub(r"[\*†‡§¶\d]+", "", text)
    parts = re.split(r",|\band\b|;|·|•", text)
    names = [p.strip(" .") for p in parts if 2 <= len(p.strip()) <= 60]
    return [n for n in names if re.search(r"[A-Za-z]", n) and len(n.split()) <= 5]


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #


def parse(extracted: ExtractedDocument) -> ParsedDocument:
    blocks = extracted.blocks
    body = _body_font_size(blocks)
    page_heights = {i + 1: h for i, (_, h) in enumerate(extracted.page_sizes)}

    # Running headers/footers repeat verbatim on many pages.
    line_counts = Counter(b.text.strip() for b in blocks if len(b.text) < 120)
    repeated = {t for t, c in line_counts.items() if c >= 3 and extracted.page_count >= 3}

    # ---- Front matter -------------------------------------------------------
    first_page = [b for b in blocks if b.page == 1 and not _is_noise(b, body, page_heights.get(1, 800), repeated)]
    title = ""
    title_block: Block | None = None
    if first_page:
        candidates = [b for b in first_page if 4 <= len(b.text) <= 300 and b.bbox[1] < page_heights.get(1, 800) * 0.5]
        if candidates:
            title_block = max(candidates, key=lambda b: (b.font_size, -b.bbox[1]))
            title = _clean_title(title_block.text)
    meta_title = (extracted.metadata.get("title") or "").strip()
    if not title and 4 <= len(meta_title) <= 300:
        title = meta_title

    authors: list[str] = []
    affiliations: list[str] = []
    abstract: str | None = None
    keywords: list[str] = []
    doi: str | None = None
    year: int | None = None
    venue: str | None = None

    front_text = " ".join(b.text for b in first_page)
    if m := _DOI.search(front_text):
        doi = m.group(1).rstrip(".,;")
    if m := _YEAR.search(front_text):
        year = int(m.group(1))
    for b in first_page[:12]:
        if re.search(r"\b(Proceedings|Conference|Journal|Transactions|Workshop|Symposium|arXiv)\b", b.text) and len(b.text) < 160:
            venue = b.text.strip()
            break

    # ---- Sections & paragraphs ---------------------------------------------
    sections: list[ParsedSection] = []
    current = ParsedSection(title="Front Matter", kind="front_matter", number=None, start_page=1)
    seen_body_heading = False
    after_title = title_block is None

    def push_section(sec: ParsedSection) -> None:
        if sec.paragraphs or sec.kind not in {"front_matter"}:
            sections.append(sec)

    for b in blocks:
        text = b.text.strip()
        if not text:
            continue
        if b is title_block:
            after_title = True
            continue
        if _is_noise(b, body, page_heights.get(b.page, 800), repeated):
            continue

        is_heading, number, heading_title = _looks_like_heading(b, body)
        if is_heading:
            kind = classify_section(heading_title)
            # "Abstract" / "Keywords" often appear as inline labels.
            if kind == "keywords":
                continue
            push_section(current)
            current = ParsedSection(title=heading_title, kind=kind, number=number, start_page=b.page)
            seen_body_heading = seen_body_heading or kind not in {"abstract", "front_matter"}
            continue

        # Inline "Abstract— ..." or "Keywords: ..." paragraphs.
        if re.match(r"^abstract\b", text, re.I) and len(text) > 40 and current.kind in {"front_matter", "abstract"}:
            body_text = re.sub(r"^abstract\s*[—:\-–.]*\s*", "", text, flags=re.I)
            if current.kind != "abstract":
                push_section(current)
                current = ParsedSection(title="Abstract", kind="abstract", number=None, start_page=b.page)
            current.paragraphs.append(ParsedParagraph(text=body_text, page=b.page, bbox=b.bbox))
            continue
        if re.match(r"^(keywords?|index terms)\s*[—:\-–]", text, re.I):
            kw = re.sub(r"^(keywords?|index terms)\s*[—:\-–]\s*", "", text, flags=re.I)
            keywords = [k.strip(" .") for k in re.split(r"[;,·]", kw) if k.strip()]
            continue

        # Front matter before the abstract: authors / affiliations.
        if current.kind == "front_matter" and after_title and not seen_body_heading:
            if _EMAIL.search(text) or re.search(r"\b(University|Institute|Department|Laboratory|Lab|School|College|Inc\.|Ltd|Corporation)\b", text):
                affiliations.append(_EMAIL.sub("", text).strip(" ,;"))
            elif len(text) < 200 and not authors:
                authors = _split_authors(text)
            elif len(text) < 200 and len(authors) < 12:
                authors.extend(_split_authors(text))
            continue

        kind = "paragraph"
        if _CAPTION.match(text):
            kind = "caption"
        elif current.kind == "references":
            kind = "reference"
        elif _is_equation(text):
            kind = "equation"
        elif re.match(r"^([•\-–●▪]|\(?\d{1,2}[\).]|[a-z][\).])\s", text):
            kind = "list"

        # Merge continuation fragments (column / page breaks) for prose.
        if kind == "paragraph" and current.paragraphs:
            last = current.paragraphs[-1]
            if last.kind == "paragraph" and _should_merge(last.text, text):
                joiner = "" if last.text.endswith("-") else " "
                last.text = (last.text[:-1] if last.text.endswith("-") else last.text) + joiner + text
                continue
        if kind == "reference" and current.paragraphs:
            last = current.paragraphs[-1]
            if last.kind == "reference" and not _REFERENCE_ITEM.match(text):
                last.text = f"{last.text} {text}"
                continue

        current.paragraphs.append(ParsedParagraph(text=text, page=b.page, kind=kind, bbox=b.bbox))
    push_section(current)

    # Fall back to a single section when no headings were found at all.
    if not sections:
        sections = [ParsedSection(title="Paper", kind="other", number=None, start_page=1,
                                  paragraphs=[ParsedParagraph(text=b.text, page=b.page, bbox=b.bbox) for b in blocks])]

    abstract_sec = next((s for s in sections if s.kind == "abstract"), None)
    if abstract_sec and abstract_sec.paragraphs:
        abstract = " ".join(p.text for p in abstract_sec.paragraphs if p.kind == "paragraph")

    # ---- Figures & tables ---------------------------------------------------
    figures = _attach_figures(extracted.images, sections)
    tables = _attach_tables(extracted.tables, sections)

    return ParsedDocument(
        title=title or "Untitled paper",
        authors=authors[:20],
        affiliations=affiliations[:10],
        abstract=abstract,
        keywords=keywords,
        year=year,
        doi=doi,
        venue=venue,
        sections=sections,
        figures=figures,
        tables=tables,
    )


def _captions(sections: list[ParsedSection], prefix: str) -> list[tuple[int, ParsedParagraph, str | None]]:
    out = []
    for si, s in enumerate(sections):
        for p in s.paragraphs:
            if p.kind != "caption":
                continue
            m = _CAPTION.match(p.text)
            if not m:
                continue
            label = m.group("label")
            if label.lower().startswith(prefix):
                out.append((si, p, label))
    return out


def _nearest(items, page: int, bbox: tuple[float, float, float, float]):
    """Closest caption on the same page (by vertical distance)."""
    best = None
    best_d = 1e9
    for si, p, label in items:
        if p.page != page or p.bbox is None:
            continue
        d = min(abs(p.bbox[1] - bbox[3]), abs(bbox[1] - p.bbox[3]))
        if d < best_d:
            best_d, best = d, (si, p, label)
    return best


def _attach_figures(images: list[ImageBlock], sections: list[ParsedSection]) -> list[ParsedFigure]:
    caps = _captions(sections, "fig")
    used: set[int] = set()
    figures: list[ParsedFigure] = []
    for img in images:
        match = _nearest([c for c in caps if id(c[1]) not in used], img.page, img.bbox)
        if match:
            si, p, label = match
            used.add(id(p))
            figures.append(ParsedFigure(page=img.page, caption=p.text, label=label.replace("Fig.", "Figure").replace("FIGURE", "Figure"), png=img.png, section_index=si))
        else:
            si = _section_on_page(sections, img.page)
            figures.append(ParsedFigure(page=img.page, caption=f"Figure on page {img.page}", label=None, png=img.png, section_index=si))
    return figures


def _attach_tables(tables: list[TableBlock], sections: list[ParsedSection]) -> list[ParsedTable]:
    caps = _captions(sections, "table")
    used: set[int] = set()
    out: list[ParsedTable] = []
    for t in tables:
        match = _nearest([c for c in caps if id(c[1]) not in used], t.page, t.bbox)
        if match:
            si, p, label = match
            used.add(id(p))
            out.append(ParsedTable(page=t.page, caption=p.text, label=label.title(), rows=t.rows, section_index=si))
        else:
            si = _section_on_page(sections, t.page)
            out.append(ParsedTable(page=t.page, caption=f"Table on page {t.page}", label=None, rows=t.rows, section_index=si))
    # Captions whose grid could not be detected still deserve an entry so the
    # sidebar lists every table of the paper.
    for si, p, label in caps:
        if id(p) not in used:
            out.append(ParsedTable(page=p.page, caption=p.text, label=label.title(), rows=[], section_index=si))
    out.sort(key=lambda t: (t.page, t.label or ""))
    return out


def _section_on_page(sections: list[ParsedSection], page: int) -> int | None:
    for i, s in enumerate(sections):
        if s.start_page <= page <= s.end_page:
            return i
    return None
