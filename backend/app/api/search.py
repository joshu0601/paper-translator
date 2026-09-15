from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.documents import get_document_or_404
from app.database import get_db
from app.models import Document, Paragraph, Section
from app.schemas import SearchRequest, SearchResult
from app.services.rag import retrieve

router = APIRouter(prefix="/api/documents", tags=["search"])


def _preview(text: str, query: str, width: int = 220) -> str:
    idx = text.lower().find(query.lower())
    if idx < 0:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, idx - width // 3)
    end = min(len(text), idx + len(query) + width * 2 // 3)
    return ("…" if start > 0 else "") + text[start:end] + ("…" if end < len(text) else "")


@router.post("/{document_id}/search", response_model=list[SearchResult])
def search(req: SearchRequest, doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    titles = {
        s.id: (f"{s.section_number} {s.title}" if s.section_number else s.title)
        for s in db.query(Section).filter(Section.document_id == doc.id).all()
    }

    if req.type == "exact":
        pattern = re.compile(re.escape(req.query.strip()), re.I)
        rows = db.query(Paragraph).filter(Paragraph.document_id == doc.id).order_by(Paragraph.order).all()
        results = []
        for p in rows:
            if pattern.search(p.original_text) or (p.translated_text and pattern.search(p.translated_text)):
                source = p.original_text if pattern.search(p.original_text) else (p.translated_text or "")
                results.append(
                    SearchResult(
                        paragraph_id=p.id, section_id=p.section_id, section_title=titles.get(p.section_id, ""),
                        page=p.page_number, preview=_preview(source, req.query.strip()),
                    )
                )
            if len(results) >= req.limit:
                break
        return results

    hits = retrieve(db, doc.id, req.query, top_k=req.limit)
    results: list[SearchResult] = []
    seen: set[str] = set()
    for h in hits:
        pid = h.chunk.paragraph_ids[0] if h.chunk.paragraph_ids else None
        if not pid or pid in seen:
            continue
        seen.add(pid)
        p = db.get(Paragraph, pid)
        if not p:
            continue
        results.append(
            SearchResult(
                paragraph_id=p.id, section_id=p.section_id, section_title=titles.get(p.section_id, ""),
                page=p.page_number, preview=_preview(h.chunk.text, ""), score=max(0.0, min(1.0, h.score)),
            )
        )
    return results
