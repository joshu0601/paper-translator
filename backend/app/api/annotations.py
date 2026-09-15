"""Notes & highlights (SPEC §40–41, §54)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.documents import get_document_or_404
from app.database import get_db
from app.models import Document, Highlight, Note, Paragraph
from app.schemas import HighlightCreate, HighlightOut, NoteCreate, NoteOut

router = APIRouter(prefix="/api", tags=["annotations"])


def _check_paragraph(db: Session, doc: Document, paragraph_id: str) -> None:
    p = db.get(Paragraph, paragraph_id)
    if p is None or p.document_id != doc.id:
        raise HTTPException(status_code=400, detail="Unknown paragraph for this document")


@router.get("/documents/{document_id}/notes", response_model=list[NoteOut])
def list_notes(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    return db.query(Note).filter(Note.document_id == doc.id).order_by(Note.created_at.desc()).all()


@router.post("/documents/{document_id}/notes", response_model=NoteOut, status_code=201)
def create_note(body: NoteCreate, doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    _check_paragraph(db, doc, body.paragraph_id)
    note = Note(document_id=doc.id, paragraph_id=body.paragraph_id, selected_text=body.selected_text, content=body.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: str, db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return None


@router.get("/documents/{document_id}/highlights", response_model=list[HighlightOut])
def list_highlights(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    return db.query(Highlight).filter(Highlight.document_id == doc.id).order_by(Highlight.created_at).all()


@router.post("/documents/{document_id}/highlights", response_model=HighlightOut, status_code=201)
def create_highlight(body: HighlightCreate, doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    _check_paragraph(db, doc, body.paragraph_id)
    if body.end_offset <= body.start_offset:
        raise HTTPException(status_code=400, detail="end_offset must be greater than start_offset")
    hl = Highlight(
        document_id=doc.id, paragraph_id=body.paragraph_id, selected_text=body.selected_text,
        start_offset=body.start_offset, end_offset=body.end_offset, color=body.color,
    )
    db.add(hl)
    db.commit()
    db.refresh(hl)
    return hl


@router.delete("/highlights/{highlight_id}", status_code=204)
def delete_highlight(highlight_id: str, db: Session = Depends(get_db)):
    hl = db.get(Highlight, highlight_id)
    if hl is None:
        raise HTTPException(status_code=404, detail="Highlight not found")
    db.delete(hl)
    db.commit()
    return None
