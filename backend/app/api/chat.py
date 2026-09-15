from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.documents import get_document_or_404
from app.database import get_db
from app.models import ChatMessage, ChatSession, Document
from app.schemas import ChatMessageOut, ChatRequest, ChatResponse, ChatSessionOut
from app.services.chat import answer_question

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/documents/{document_id}/chat", response_model=ChatResponse)
def chat(req: ChatRequest, doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    if doc.status != "ready":
        raise HTTPException(status_code=409, detail="Document is not ready yet")
    try:
        answer, citations, session, reply = answer_question(db, doc, req)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ChatResponse(answer=answer, citations=citations, session_id=session.id, message_id=reply.id)


@router.get("/documents/{document_id}/chat/sessions", response_model=list[ChatSessionOut])
def list_sessions(doc: Document = Depends(get_document_or_404), db: Session = Depends(get_db)):
    return db.query(ChatSession).filter(ChatSession.document_id == doc.id).order_by(ChatSession.created_at.desc()).all()


@router.get("/chat/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def list_messages(session_id: str, db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
