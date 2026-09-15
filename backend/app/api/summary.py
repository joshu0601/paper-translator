from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.documents import get_document_or_404
from app.database import get_db
from app.models import Document, Summary, Terminology
from app.schemas import SummaryLength, SummaryOut, TerminologyOut
from app.services.summary import generate_summary

router = APIRouter(prefix="/api/documents", tags=["summary"])


def _ensure_ready(doc: Document) -> None:
    if doc.status != "ready":
        raise HTTPException(status_code=409, detail="Document is not ready yet")


@router.get("/{document_id}/summary", response_model=SummaryOut)
def get_summary(length: SummaryLength = Query("short"), doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    _ensure_ready(doc)
    row = db.query(Summary).filter(Summary.document_id == doc.id, Summary.length == length).one_or_none()
    if row is None:
        row = generate_summary(db, doc, length)
    return row


@router.post("/{document_id}/summary", response_model=SummaryOut)
def regenerate_summary(length: SummaryLength = Query("short"), doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    _ensure_ready(doc)
    return generate_summary(db, doc, length)


@router.get("/{document_id}/terminology", response_model=list[TerminologyOut])
def get_terminology(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    return db.query(Terminology).filter(Terminology.document_id == doc.id).order_by(Terminology.term).all()
