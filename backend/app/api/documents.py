from __future__ import annotations

import io
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Document, Figure, Paragraph, Section, Table
from app.schemas import DocumentOut, DocumentPatch, FigureOut, ParagraphOut, SectionOut, TableOut
from app.services import pipeline
from app.services.demo import TITLE as DEMO_TITLE, build_demo_pdf
from app.services.pdf import page_count
from app.services.storage import get_storage

router = APIRouter(prefix="/api/documents", tags=["documents"])


def get_document_or_404(document_id: str, db: Session = Depends(get_db)) -> Document:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w.\-]+", "_", name)[:120] or "paper.pdf"


def _create_document(db: Session, *, file_name: str, data: bytes, title: str | None = None) -> Document:
    try:
        pages = page_count(data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid PDF: {exc}") from exc

    doc = Document(
        title=title or file_name,
        file_name=file_name,
        file_size=len(data),
        page_count=pages,
        storage_key="",
        status="uploaded",
        steps=pipeline.initial_steps(),
    )
    db.add(doc)
    db.flush()
    doc.storage_key = f"{doc.id}/{_safe_name(file_name)}"
    get_storage().put(doc.storage_key, data)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).limit(100).all()


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(file: UploadFile, db: Session = Depends(get_db)):
    settings = get_settings()
    if not (file.filename or "").lower().endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB")
    doc = _create_document(db, file_name=file.filename or "paper.pdf", data=data)
    pipeline.start_background(pipeline.run_pipeline, doc.id)
    return doc


@router.post("/demo", response_model=DocumentOut, status_code=201)
def create_demo_document(db: Session = Depends(get_db)):
    data = build_demo_pdf()
    doc = _create_document(db, file_name="drl-jora-demo.pdf", data=data, title=DEMO_TITLE)
    pipeline.start_background(pipeline.run_pipeline, doc.id)
    return doc


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(doc: Document = Depends(get_document_or_404)):
    return doc


@router.patch("/{document_id}", response_model=DocumentOut)
def update_document(patch: DocumentPatch, doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    for key, value in patch.model_dump(exclude_unset=True).items():
        setattr(doc, key, value)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    try:
        get_storage().delete(doc.id)
    except Exception:  # storage cleanup is best effort
        pass
    db.delete(doc)
    db.commit()
    return None


@router.get("/{document_id}/file")
def get_file(doc: Document = Depends(get_document_or_404)):
    storage = get_storage()
    path = storage.local_path(doc.storage_key)
    if path:
        return FileResponse(path, media_type="application/pdf", filename=doc.file_name)
    return StreamingResponse(io.BytesIO(storage.get(doc.storage_key)), media_type="application/pdf")


@router.post("/{document_id}/process", response_model=DocumentOut)
def reprocess(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    """Re-run the whole pipeline (e.g. after a failure)."""
    if doc.status == "processing":
        raise HTTPException(status_code=409, detail="Document is still processing")
    doc.status = "processing"
    doc.error = None
    doc.steps = pipeline.initial_steps()
    db.commit()
    db.refresh(doc)
    pipeline.start_background(pipeline.run_pipeline, doc.id)
    return doc


@router.post("/{document_id}/translate", response_model=DocumentOut)
def retranslate(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    if doc.status == "processing":
        raise HTTPException(status_code=409, detail="Document is still processing")
    doc.status = "processing"
    steps = [dict(s) for s in doc.steps]
    for s in steps:
        if s["key"] == "translate":
            s.update(status="running", percent=0)
    doc.steps = steps
    db.commit()
    db.refresh(doc)
    pipeline.start_background(pipeline.run_retranslate, doc.id)
    return doc


@router.get("/{document_id}/sections", response_model=list[SectionOut])
def get_sections(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    return db.query(Section).filter(Section.document_id == doc.id).order_by(Section.order).all()


@router.get("/{document_id}/paragraphs", response_model=list[ParagraphOut])
def get_paragraphs(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    return db.query(Paragraph).filter(Paragraph.document_id == doc.id).order_by(Paragraph.order).all()


@router.get("/{document_id}/figures", response_model=list[FigureOut])
def get_figures(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    rows = db.query(Figure).filter(Figure.document_id == doc.id).order_by(Figure.order).all()
    return [
        FigureOut(
            id=f.id, document_id=f.document_id, section_id=f.section_id, page_number=f.page_number,
            caption=f.caption, label=f.label, image_url=f"/api/documents/{doc.id}/figures/{f.id}/image",
        )
        for f in rows
    ]


@router.get("/{document_id}/figures/{figure_id}/image")
def get_figure_image(figure_id: str, doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    fig = db.get(Figure, figure_id)
    if fig is None or fig.document_id != doc.id:
        raise HTTPException(status_code=404, detail="Figure not found")
    storage = get_storage()
    path = storage.local_path(fig.storage_key)
    if path:
        return FileResponse(path, media_type="image/png")
    return StreamingResponse(io.BytesIO(storage.get(fig.storage_key)), media_type="image/png")


@router.get("/{document_id}/tables", response_model=list[TableOut])
def get_tables(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    return db.query(Table).filter(Table.document_id == doc.id).order_by(Table.order).all()
