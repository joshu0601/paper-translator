"""Structured paper summaries (SPEC §38–39, §55)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Document, Paragraph, Section, Summary
from app.schemas import Citation
from app.services.chat import ContextUnit, extract_citations, format_context, make_tag
from app.services.llm import LLMMessage, get_llm
from app.services.chat import SYSTEM_PROMPT

SUMMARY_SECTIONS = [
    "Research Problem", "Motivation", "Main Contributions", "Methodology", "System Model", "Datasets",
    "Experimental Setup", "Baselines", "Evaluation Metrics", "Results", "Limitations", "Future Work",
    "Key Takeaways",
]

LENGTH_INSTRUCTIONS = {
    "one_sentence": "Write exactly ONE sentence in Traditional Chinese that captures the paper's problem, method and main result, followed by one citation tag.",
    "short": "Write a short structured summary in Traditional Chinese (about 150–250 words). Use these headings, skipping any the paper does not support: "
    + ", ".join(SUMMARY_SECTIONS) + ". One or two bullet points per heading, each with a citation tag.",
    "detailed": "Write a detailed structured summary in Traditional Chinese. Use these Markdown headings in order, writing「論文未提供」when the paper does not support one: "
    + ", ".join(SUMMARY_SECTIONS) + ". Cite with the given citation tags after each factual statement.",
}


def _representative_units(db: Session, doc: Document, per_section: int = 3) -> list[ContextUnit]:
    sections = db.query(Section).filter(Section.document_id == doc.id).order_by(Section.order).all()
    units: list[ContextUnit] = []
    for sec in sections:
        if sec.kind in {"references", "acknowledgements", "front_matter", "keywords"}:
            continue
        title = f"{sec.section_number} {sec.title}" if sec.section_number else sec.title
        paras = (
            db.query(Paragraph)
            .filter(Paragraph.section_id == sec.id, Paragraph.kind == "paragraph")
            .order_by(Paragraph.order)
            .all()
        )
        n = len(paras) if sec.kind in {"abstract", "conclusion"} else per_section
        for p in paras[:n]:
            units.append(ContextUnit(p, title, make_tag(p.page_number, title, p.id)))
    return units[:45]


def generate_summary(db: Session, doc: Document, length: str) -> Summary:
    units = _representative_units(db, doc)
    prompt = (
        f"Paper title: {doc.title}\n\nRetrieved paper context:\n\n{format_context(units)}\n\n"
        f"{LENGTH_INSTRUCTIONS[length]}\n\nQuestion: 請摘要這篇論文的研究問題、方法、實驗、結果、貢獻與限制。"
    )
    text = get_llm().chat([LLMMessage("user", prompt)], system=SYSTEM_PROMPT, max_tokens=4000, temperature=0.2).text.strip()
    citations: list[Citation] = extract_citations(db, doc, text, units)

    row = db.query(Summary).filter(Summary.document_id == doc.id, Summary.length == length).one_or_none()
    if row is None:
        row = Summary(document_id=doc.id, length=length)
        db.add(row)
    row.content = text
    row.citations = [c.model_dump(by_alias=True) for c in citations]
    db.commit()
    db.refresh(row)
    return row
