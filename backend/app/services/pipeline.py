"""Processing pipeline (SPEC §7):

Upload → Text extraction → Structure detection → Paragraph segmentation →
Figure / table detection → Translation → Embeddings → Ready

Runs in a background thread; progress is persisted on `documents.steps` so the
frontend can poll it.
"""

from __future__ import annotations

import logging
import threading
import traceback

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import Document, Figure, Paragraph, Section, Table, Terminology, Translation
from app.services import layout, rag
from app.services.parsing import ParsedDocument, parse
from app.services.pdf import extract
from app.services.storage import get_storage
from app.services.text import sha256
from app.services.translation import DEFAULT_TERMINOLOGY, extract_term_candidates, get_translator

log = logging.getLogger(__name__)

STEP_DEFS: list[tuple[str, str]] = [
    ("upload", "Uploading PDF"),
    ("extract", "Extracting text"),
    ("structure", "Detecting document structure"),
    ("parse", "Parsing paragraphs"),
    ("translate", "Translating paper"),
    ("layout", "Rendering translated pages"),
    ("index", "Creating AI index"),
]

TRANSLATABLE_KINDS = {"paragraph", "list", "caption"}
DEFAULT_PAGE_DPI = 120


def initial_steps(done: tuple[str, ...] = ("upload",)) -> list[dict]:
    return [
        {"key": k, "label": label, "status": "done" if k in done else "pending", "percent": None}
        for k, label in STEP_DEFS
    ]


class StepReporter:
    def __init__(self, db: Session, doc: Document):
        self.db = db
        self.doc = doc

    def _set(self, key: str, **fields) -> None:
        steps = [dict(s) for s in (self.doc.steps or initial_steps())]
        for s in steps:
            if s["key"] == key:
                s.update(fields)
        self.doc.steps = steps
        self.db.add(self.doc)
        self.db.commit()

    def start(self, key: str) -> None:
        self._set(key, status="running", percent=None)

    def progress(self, key: str, percent: int) -> None:
        self._set(key, status="running", percent=int(percent))

    def done(self, key: str) -> None:
        self._set(key, status="done", percent=None)

    def fail(self, key: str, error: str) -> None:
        self.db.rollback()  # the failed step may have left the session unusable
        self.doc = self.db.merge(self.doc)
        self._set(key, status="failed", percent=None)
        self.doc.status = "failed"
        self.doc.error = error[:2000]
        self.db.add(self.doc)
        self.db.commit()


# --------------------------------------------------------------------------- #
# Persisting parsed structure
# --------------------------------------------------------------------------- #


def persist_parsed(db: Session, doc: Document, parsed: ParsedDocument) -> None:
    storage = get_storage()

    # Replace any previous parse result.
    db.query(Paragraph).filter(Paragraph.document_id == doc.id).delete()
    db.query(Figure).filter(Figure.document_id == doc.id).delete()
    db.query(Table).filter(Table.document_id == doc.id).delete()
    db.query(Section).filter(Section.document_id == doc.id).delete()
    db.flush()

    # (Re)processing always refreshes detected metadata; users can PATCH it afterwards.
    doc.title = parsed.title
    doc.authors = parsed.authors
    doc.affiliations = parsed.affiliations
    doc.abstract = parsed.abstract
    doc.keywords = parsed.keywords
    doc.year = parsed.year
    doc.doi = parsed.doi
    doc.venue = parsed.venue

    section_ids: list[str] = []
    for si, sec in enumerate(parsed.sections):
        sid = f"{doc.id}__section_{si + 1:02d}"
        section_ids.append(sid)
        db.add(
            Section(
                id=sid,
                document_id=doc.id,
                title=sec.title,
                section_number=sec.number,
                kind=sec.kind,
                order=si,
                start_page=sec.start_page,
                end_page=sec.end_page,
            )
        )
    # Sections must exist before paragraphs reference them (no ORM relationship
    # links the two, so the unit of work cannot order the inserts itself).
    db.flush()

    para_no = 0
    for si, sec in enumerate(parsed.sections):
        sid = section_ids[si]
        for p in sec.paragraphs:
            para_no += 1
            bbox = None
            if p.bbox:
                x0, y0, x1, y1 = p.bbox
                bbox = {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}
            db.add(
                Paragraph(
                    id=f"{doc.id}__paragraph_{para_no:04d}",
                    document_id=doc.id,
                    section_id=sid,
                    page_number=p.page,
                    original_text=p.text,
                    order=para_no,
                    kind=p.kind,
                    bounding_box=bbox,
                    boxes=[box.as_dict() for box in p.boxes],
                )
            )

    for fi, fig in enumerate(parsed.figures):
        key = f"{doc.id}/figures/figure_{fi + 1:03d}.png"
        storage.put(key, fig.png)
        db.add(
            Figure(
                id=f"{doc.id}__figure_{fi + 1:03d}",
                document_id=doc.id,
                section_id=section_ids[fig.section_index] if fig.section_index is not None and fig.section_index < len(section_ids) else None,
                page_number=fig.page,
                caption=fig.caption,
                label=fig.label,
                storage_key=key,
                order=fi,
            )
        )
    for ti, tab in enumerate(parsed.tables):
        db.add(
            Table(
                id=f"{doc.id}__table_{ti + 1:03d}",
                document_id=doc.id,
                section_id=section_ids[tab.section_index] if tab.section_index is not None and tab.section_index < len(section_ids) else None,
                page_number=tab.page,
                caption=tab.caption,
                label=tab.label,
                rows=tab.rows,
                order=ti,
            )
        )
    db.commit()


# --------------------------------------------------------------------------- #
# Translation with cache + terminology memory
# --------------------------------------------------------------------------- #


def _terminology_for(db: Session, doc: Document, sample_text: str) -> dict[str, str]:
    existing = {t.term: t.translation for t in db.query(Terminology).filter(Terminology.document_id == doc.id).all()}
    glossary = dict(DEFAULT_TERMINOLOGY)
    glossary.update(existing)
    candidates = [c for c in extract_term_candidates(sample_text) if c not in glossary]
    if candidates:
        try:
            learned = get_translator().build_terminology(sample_text[:4000], candidates)
        except Exception as exc:  # pragma: no cover - provider failure is non-fatal
            log.warning("terminology extraction failed: %s", exc)
            learned = {}
        for term, zh in learned.items():
            glossary[term] = zh
            db.add(Terminology(document_id=doc.id, term=term, translation=zh))
        db.commit()
    return glossary


def translate_document(db: Session, doc: Document, reporter: StepReporter, *, force: bool = False) -> None:
    s = get_settings()
    translator = get_translator()
    reporter.start("translate")

    paragraphs = (
        db.query(Paragraph)
        .filter(Paragraph.document_id == doc.id, Paragraph.kind.in_(TRANSLATABLE_KINDS))
        .order_by(Paragraph.order)
        .all()
    )
    if not force:
        paragraphs = [p for p in paragraphs if not p.translated_text]
    total = len(paragraphs)
    if total == 0:
        reporter.done("translate")
        return

    sample = "\n".join(p.original_text for p in paragraphs[:60])
    glossary = _terminology_for(db, doc, sample)

    def cached_row(h: str) -> Translation | None:
        return (
            db.query(Translation)
            .filter(Translation.source_hash == h, Translation.provider == translator.name)
            .one_or_none()
        )

    # Papers repeat text (running footers, licence lines, table headers...).
    # Track what this run has already translated so identical paragraphs are
    # translated once and never produce duplicate cache rows.
    seen: dict[str, str] = {}

    done = 0
    batch_size = max(1, s.translation_batch_size)
    for i in range(0, total, batch_size):
        batch = paragraphs[i : i + batch_size]
        pending: dict[str, list[Paragraph]] = {}
        for p in batch:
            h = sha256(p.original_text)
            if h in seen:
                p.translated_text = seen[h]
                continue
            cached = cached_row(h) if not force else None
            if cached:
                p.translated_text = cached.translated_text
                seen[h] = cached.translated_text
            else:
                pending.setdefault(h, []).append(p)
        if pending:
            sources = [group[0].original_text for group in pending.values()]
            translated = translator.translate_batch(sources, glossary)
            for (h, group), zh in zip(pending.items(), translated):
                seen[h] = zh
                for p in group:
                    p.translated_text = zh
                row = cached_row(h)
                if row:
                    row.translated_text = zh
                else:
                    db.add(Translation(source_hash=h, provider=translator.name, source_text=group[0].original_text, translated_text=zh))
        done += len(batch)
        db.commit()
        reporter.progress("translate", round(done * 100 / total))
    reporter.done("translate")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def translated_pdf_key(doc: Document) -> str:
    return f"{doc.id}/translated.pdf"


def render_layout(db: Session, doc: Document, reporter: StepReporter) -> None:
    """Build the layout-preserving translated PDF and drop stale page renders."""
    reporter.start("layout")
    storage = get_storage()
    paragraphs = db.query(Paragraph).filter(Paragraph.document_id == doc.id).order_by(Paragraph.order).all()
    pdf_bytes = storage.get(doc.storage_key)
    translated = layout.build_translated_pdf(pdf_bytes, paragraphs)
    storage.put(translated_pdf_key(doc), translated)
    storage.delete(f"{doc.id}/pages/translated")
    doc.layout_version = (doc.layout_version or 0) + 1
    db.commit()
    # Pre-render both variants at the reader's default DPI so the first view
    # does not wait on rasterisation (the API renders other DPIs on demand).
    total = max(doc.page_count, 1)
    for i in range(1, total + 1):
        for variant, source in (("original", pdf_bytes), ("translated", translated)):
            key = f"{doc.id}/pages/{variant}/{i}_{DEFAULT_PAGE_DPI}.png"
            if not storage.exists(key):
                storage.put(key, layout.render_page(source, i, DEFAULT_PAGE_DPI))
        reporter.progress("layout", round(i * 100 / total))
    reporter.done("layout")


def index_document(db: Session, doc: Document, reporter: StepReporter) -> None:
    reporter.start("index")
    sections = db.query(Section).filter(Section.document_id == doc.id).order_by(Section.order).all()
    paragraphs = db.query(Paragraph).filter(Paragraph.document_id == doc.id).order_by(Paragraph.order).all()
    chunks = rag.build_chunks(sections, paragraphs)
    rag.index_document(db, doc.id, chunks)
    reporter.done("index")


def run_pipeline(document_id: str, *, parsed: ParsedDocument | None = None) -> None:
    """Full pipeline. When `parsed` is given (demo paper) PDF extraction is skipped."""
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            return
        reporter = StepReporter(db, doc)
        doc.status = "processing"
        doc.error = None
        db.commit()

        step = "extract"
        try:
            if parsed is None:
                reporter.start("extract")
                pdf_bytes = get_storage().get(doc.storage_key)
                extracted = extract(pdf_bytes)
                doc.page_count = extracted.page_count
                reporter.done("extract")

                step = "structure"
                reporter.start("structure")
                parsed = parse(extracted)
                reporter.done("structure")
            else:
                reporter.done("extract")
                reporter.done("structure")

            step = "parse"
            reporter.start("parse")
            persist_parsed(db, doc, parsed)
            reporter.done("parse")

            step = "translate"
            translate_document(db, doc, reporter)

            step = "layout"
            render_layout(db, doc, reporter)

            step = "index"
            index_document(db, doc, reporter)

            doc.status = "ready"
            db.commit()
        except Exception as exc:
            log.error("pipeline failed for %s at %s: %s\n%s", document_id, step, exc, traceback.format_exc())
            reporter.fail(step, f"{type(exc).__name__}: {exc}")
    finally:
        db.close()


def run_retranslate(document_id: str) -> None:
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            return
        reporter = StepReporter(db, doc)
        doc.status = "processing"
        db.commit()
        step = "translate"
        try:
            translate_document(db, doc, reporter, force=True)
            step = "layout"
            render_layout(db, doc, reporter)
            doc.status = "ready"
            db.commit()
        except Exception as exc:
            reporter.fail(step, f"{type(exc).__name__}: {exc}")
    finally:
        db.close()


def resume_interrupted() -> list[str]:
    """Re-queue documents left in `processing` by a server restart (the pipeline
    runs in a daemon thread, so a reload/crash abandons it mid-way)."""
    db = SessionLocal()
    try:
        stuck = db.query(Document).filter(Document.status == "processing").all()
        ids = [d.id for d in stuck]
        for doc in stuck:
            doc.steps = initial_steps()
            doc.error = None
        db.commit()
    finally:
        db.close()
    for doc_id in ids:
        log.info("resuming interrupted processing for %s", doc_id)
        start_background(run_pipeline, doc_id)
    return ids


def start_background(target, *args, **kwargs) -> threading.Thread:
    t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t
