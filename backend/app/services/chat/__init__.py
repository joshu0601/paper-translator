"""Document-grounded chat: retrieval, prompting, citation extraction (SPEC §22–37, §71, §73)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import ChatMessage, ChatSession, Document, Paragraph, Section
from app.schemas import ChatRequest, Citation
from app.services.llm import LLMMessage, get_llm
from app.services.rag import retrieve

SYSTEM_PROMPT = """You are PaperAI, an academic research assistant.

Your primary task is to help the user understand the currently uploaded academic paper.

Always prioritize information contained in the paper.

When answering:

1. Answer the user's question directly.
2. Explain difficult concepts clearly.
3. Use the terminology used by the paper.
4. Cite relevant sections, pages, and paragraphs.
5. Never fabricate experimental results.
6. Never fabricate citations.
7. Clearly state when the paper does not provide enough information.
8. Distinguish between:
   - information explicitly stated in the paper
   - interpretation
   - general background knowledge

If mathematical formulas appear, explain their meaning rather than simply repeating them.

Unless the user requests otherwise, answer in Traditional Chinese."""

RAG_INSTRUCTIONS = """Use ONLY the provided retrieved paper context for factual claims about the paper.

If the retrieved context does not contain enough information, say:
目前在這篇論文中找不到足夠資訊回答這個問題。

Do not invent: methods, metrics, results, datasets, experimental settings, citations.

Answer in Traditional Chinese unless requested otherwise. Use Markdown (short paragraphs, bullet lists) and keep the answer focused.

At the end of relevant statements, provide source citations by copying the citation tag of the
context block EXACTLY as given, e.g. [Page 7 · Section 4.2 · Paragraph 73]. Only cite tags that
appear in the context. Do not cite when stating general background knowledge; mark such
statements with「（背景知識）」and interpretations with「（推論）」."""

LEVEL_INSTRUCTIONS = {
    "beginner": "Audience: complete beginner. Use intuitive explanations, simple language, everyday examples and analogies. Avoid unnecessary mathematical detail.",
    "undergraduate": "Audience: undergraduate student. Explain concepts step by step with light formalism and concrete examples.",
    "graduate": "Audience: graduate student. Cover research motivation, problem formulation, model architecture, algorithms, experimental setup and results. Include necessary formulas and explain them.",
    "researcher": "Audience: researcher. Focus on assumptions, mathematical formulation, model limitations, experimental validity, baseline fairness, generalization, ablation studies and future research directions. Be critical and precise.",
}

ACTION_INSTRUCTIONS = {
    "ask": "",
    "explain": "Task: explain the selected text. Clarify what it means, define the terms, and connect it to the rest of the paper.",
    "translate": "Task: translate the selected text into formal academic Traditional Chinese. Keep equations, variable names, model names, dataset names and citations unchanged. Then add a one-sentence note on anything ambiguous.",
    "summarize": "Task: summarize the selected text (or the paper if none) into concise key points.",
}

NOT_FOUND = "目前在這篇論文中找不到足夠資訊回答這個問題。"

_CITE_RE = re.compile(
    r"\[\s*Page\s*(?P<page>\d+)\s*[·,;\-–]\s*Section\s*(?P<section>[^·\]\n]+?)\s*[·,;\-–]\s*Paragraph\s*(?P<para>\d+)\s*\]"
)


@dataclass
class ContextUnit:
    paragraph: Paragraph
    section_title: str
    tag: str


def paragraph_number(paragraph_id: str) -> int:
    m = re.search(r"(\d+)$", paragraph_id)
    return int(m.group(1)) if m else 0


def make_tag(page: int, section_title: str, paragraph_id: str) -> str:
    return f"[Page {page} · Section {section_title} · Paragraph {paragraph_number(paragraph_id)}]"


def _section_titles(db: Session, document_id: str) -> dict[str, str]:
    rows = db.query(Section).filter(Section.document_id == document_id).all()
    return {s.id: (f"{s.section_number} {s.title}" if s.section_number else s.title) for s in rows}


def gather_context(db: Session, doc: Document, req: ChatRequest, *, top_k: int = 8) -> list[ContextUnit]:
    """Retrieve the paragraphs to ground the answer on, honouring the context mode."""
    titles = _section_titles(db, doc.id)
    query = req.message
    if req.selected_text:
        query = f"{req.selected_text}\n{req.message}"

    section_id = req.section_id if req.context == "current_section" else None
    page = req.page if req.context == "current_page" else None
    hits = retrieve(db, doc.id, query, top_k=top_k, section_id=section_id, page=page)

    # Fall back to the whole paper when a narrow scope has no index rows.
    if not hits and (section_id or page):
        hits = retrieve(db, doc.id, query, top_k=top_k)

    paragraph_ids: list[str] = []
    for h in hits:
        for pid in h.chunk.paragraph_ids:
            if pid not in paragraph_ids:
                paragraph_ids.append(pid)

    if not paragraph_ids:
        return []
    rows = db.query(Paragraph).filter(Paragraph.id.in_(paragraph_ids)).all()
    by_id = {p.id: p for p in rows}
    units: list[ContextUnit] = []
    for pid in paragraph_ids:
        p = by_id.get(pid)
        if not p:
            continue
        title = titles.get(p.section_id, "")
        units.append(ContextUnit(p, title, make_tag(p.page_number, title, p.id)))
    return units[: top_k * 3]


def format_context(units: list[ContextUnit]) -> str:
    parts = []
    for i, u in enumerate(units, 1):
        parts.append(f"[CHUNK {i}] {u.tag}\n{u.paragraph.original_text}")
    parts.append("[END OF CONTEXT]")
    return "\n\n".join(parts)


def build_prompt(doc: Document, req: ChatRequest, units: list[ContextUnit]) -> tuple[str, str]:
    """Return (system, user) prompt strings."""
    system = "\n\n".join(
        [SYSTEM_PROMPT, RAG_INSTRUCTIONS, LEVEL_INSTRUCTIONS.get(req.level, "")]
    )
    header = f"Paper title: {doc.title}\n"
    if doc.authors:
        header += f"Authors: {', '.join(doc.authors[:8])}\n"
    selected = f"\nSelected text from the paper:\n\"\"\"\n{req.selected_text.strip()}\n\"\"\"\n" if req.selected_text else ""
    action = ACTION_INSTRUCTIONS.get(req.action, "")
    user = (
        f"{header}\nRetrieved paper context:\n\n{format_context(units) if units else '(no relevant context found)'}\n"
        f"{selected}\n{action}\n\nQuestion: {req.message.strip()}"
    )
    return system, user


def extract_citations(db: Session, doc: Document, answer: str, units: list[ContextUnit]) -> list[Citation]:
    """Validate citation tags found in the answer against real paragraphs (SPEC §30)."""
    titles = _section_titles(db, doc.id)
    citations: list[Citation] = []
    seen: set[str] = set()
    for m in _CITE_RE.finditer(answer):
        pid = f"{doc.id}__paragraph_{int(m.group('para')):04d}"
        if pid in seen:
            continue
        p = db.get(Paragraph, pid)
        if not p or p.document_id != doc.id:
            continue
        seen.add(pid)
        citations.append(
            Citation(
                page=p.page_number,
                section=titles.get(p.section_id, m.group("section").strip()),
                paragraph_id=pid,
                snippet=p.original_text[:160],
            )
        )
    if not citations and units and NOT_FOUND not in answer:
        # The model answered without tags: expose the evidence it was given.
        for u in units[:3]:
            citations.append(
                Citation(page=u.paragraph.page_number, section=u.section_title,
                         paragraph_id=u.paragraph.id, snippet=u.paragraph.original_text[:160])
            )
    return citations


def _history(db: Session, session_id: str, limit: int = 6) -> list[LLMMessage]:
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return [LLMMessage(r.role, r.content[:2000]) for r in reversed(rows)]


def answer_question(db: Session, doc: Document, req: ChatRequest) -> tuple[str, list[Citation], ChatSession, ChatMessage]:
    session = db.get(ChatSession, req.session_id) if req.session_id else None
    if session is None or session.document_id != doc.id:
        session = ChatSession(document_id=doc.id, title=req.message[:80])
        db.add(session)
        db.flush()

    units = gather_context(db, doc, req)
    system, user = build_prompt(doc, req, units)
    history = _history(db, session.id)
    messages = history + [LLMMessage("user", user)]

    llm = get_llm()
    if not units and req.context != "selected_text":
        answer = NOT_FOUND
    else:
        answer = llm.chat(messages, system=system, max_tokens=3000, temperature=0.2).text.strip() or NOT_FOUND
    citations = extract_citations(db, doc, answer, units)

    db.add(ChatMessage(session_id=session.id, role="user", content=req.message, context_mode=req.context))
    reply = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        citations=[c.model_dump(by_alias=True) for c in citations],
        context_mode=req.context,
    )
    db.add(reply)
    db.commit()
    return answer, citations, session, reply
