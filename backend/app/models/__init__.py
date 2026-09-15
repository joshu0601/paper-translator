"""SQLAlchemy models (SPEC §56)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.database.session import Base

settings = get_settings()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# On PostgreSQL the embedding is a real pgvector column so similarity search runs
# in the database; on SQLite it is stored as JSON and scored in Python.
if settings.is_postgres:
    from pgvector.sqlalchemy import Vector

    EmbeddingType = Vector(settings.embedding_dimensions)
else:
    EmbeddingType = JSON()


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("doc"))
    title: Mapped[str] = mapped_column(Text, default="")
    authors: Mapped[list] = mapped_column(JSON, default=list)
    affiliations: Mapped[list] = mapped_column(JSON, default=list)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    venue: Mapped[str | None] = mapped_column(Text, nullable=True)

    file_name: Mapped[str] = mapped_column(Text)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    storage_key: Mapped[str] = mapped_column(Text)
    page_count: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    steps: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sections: Mapped[list[Section]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Section.order"
    )
    paragraphs: Mapped[list[Paragraph]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Paragraph.order"
    )
    figures: Mapped[list[Figure]] = relationship(cascade="all, delete-orphan")
    tables: Mapped[list[Table]] = relationship(cascade="all, delete-orphan")
    embeddings: Mapped[list[Embedding]] = relationship(cascade="all, delete-orphan")
    notes: Mapped[list[Note]] = relationship(cascade="all, delete-orphan")
    highlights: Mapped[list[Highlight]] = relationship(cascade="all, delete-orphan")
    chat_sessions: Mapped[list[ChatSession]] = relationship(cascade="all, delete-orphan")
    summaries: Mapped[list[Summary]] = relationship(cascade="all, delete-orphan")


class Section(Base):
    __tablename__ = "document_sections"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text)
    section_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), default="other")
    order: Mapped[int] = mapped_column(Integer)
    start_page: Mapped[int] = mapped_column(Integer, default=1)
    end_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document: Mapped[Document] = relationship(back_populates="sections")


class Paragraph(Base):
    __tablename__ = "document_paragraphs"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[str] = mapped_column(ForeignKey("document_sections.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    original_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20), default="paragraph")
    bounding_box: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    document: Mapped[Document] = relationship(back_populates="paragraphs")


class Figure(Base):
    __tablename__ = "document_figures"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    page_number: Mapped[int] = mapped_column(Integer)
    caption: Mapped[str] = mapped_column(Text, default="")
    label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    storage_key: Mapped[str] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, default=0)


class Table(Base):
    __tablename__ = "document_tables"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    page_number: Mapped[int] = mapped_column(Integer)
    caption: Mapped[str] = mapped_column(Text, default="")
    label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rows: Mapped[list] = mapped_column(JSON, default=list)
    order: Mapped[int] = mapped_column(Integer, default=0)


class Embedding(Base):
    """One RAG chunk (SPEC §26–27)."""

    __tablename__ = "document_embeddings"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    section_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    section_title: Mapped[str] = mapped_column(Text, default="")
    page_number: Mapped[int] = mapped_column(Integer)
    paragraph_ids: Mapped[list] = mapped_column(JSON, default=list)
    text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(EmbeddingType, nullable=True)
    model: Mapped[str] = mapped_column(String(100), default="")


class Translation(Base):
    """Translation cache keyed by source-text hash (SPEC §64)."""

    __tablename__ = "translations"
    __table_args__ = (UniqueConstraint("source_hash", "provider", name="uq_translation_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    source_text: Mapped[str] = mapped_column(Text)
    translated_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Terminology(Base):
    """Per-document terminology memory (SPEC §18)."""

    __tablename__ = "terminology"
    __table_args__ = (UniqueConstraint("document_id", "term", name="uq_terminology_term"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    term: Mapped[str] = mapped_column(Text)
    translation: Mapped[str] = mapped_column(Text)
    user_override: Mapped[bool] = mapped_column(Boolean, default=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(60), primary_key=True, default=lambda: new_id("chat"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    messages: Mapped[list[ChatMessage]] = relationship(
        cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(60), primary_key=True, default=lambda: new_id("msg"))
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSON, default=list)
    context_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(60), primary_key=True, default=lambda: new_id("note"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    paragraph_id: Mapped[str] = mapped_column(String(60))
    selected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Highlight(Base):
    __tablename__ = "highlights"

    id: Mapped[str] = mapped_column(String(60), primary_key=True, default=lambda: new_id("hl"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    paragraph_id: Mapped[str] = mapped_column(String(60))
    selected_text: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Summary(Base):
    __tablename__ = "summaries"
    __table_args__ = (UniqueConstraint("document_id", "length", name="uq_summary_length"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    length: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

