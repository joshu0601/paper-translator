"""RAG: paragraph-based chunking, vector storage and retrieval (SPEC §25–27)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Embedding, Paragraph, Section
from app.services.embeddings import cosine_similarity, get_embeddings

CHUNKABLE_KINDS = {"paragraph", "list", "equation", "caption"}


@dataclass
class Chunk:
    index: int
    section_id: str | None
    section_title: str
    page_number: int
    paragraph_ids: list[str]
    text: str


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


def build_chunks(sections: list[Section], paragraphs: list[Paragraph], *, target_chars: int | None = None,
                 overlap: int | None = None) -> list[Chunk]:
    s = get_settings()
    target = target_chars or s.chunk_target_chars
    overlap = s.chunk_overlap_paragraphs if overlap is None else overlap
    titles = {sec.id: (f"{sec.section_number} {sec.title}" if sec.section_number else sec.title) for sec in sections}

    chunks: list[Chunk] = []
    by_section: dict[str, list[Paragraph]] = {}
    for p in paragraphs:
        if p.kind in CHUNKABLE_KINDS and p.original_text.strip():
            by_section.setdefault(p.section_id, []).append(p)

    for sec in sections:
        paras = by_section.get(sec.id, [])
        i = 0
        while i < len(paras):
            group: list[Paragraph] = []
            size = 0
            j = i
            while j < len(paras) and (size == 0 or size + len(paras[j].original_text) <= target):
                group.append(paras[j])
                size += len(paras[j].original_text)
                j += 1
            chunks.append(
                Chunk(
                    index=len(chunks),
                    section_id=sec.id,
                    section_title=titles.get(sec.id, sec.title),
                    page_number=group[0].page_number,
                    paragraph_ids=[p.id for p in group],
                    text="\n\n".join(p.original_text for p in group),
                )
            )
            # Slight overlap between consecutive chunks (SPEC §26).
            i = max(j - overlap, i + 1) if j < len(paras) else j
    return chunks


def index_document(db: Session, document_id: str, chunks: list[Chunk]) -> None:
    provider = get_embeddings()
    db.query(Embedding).filter(Embedding.document_id == document_id).delete()
    vectors = provider.embed([c.text for c in chunks]) if chunks else []
    for chunk, vec in zip(chunks, vectors):
        db.add(
            Embedding(
                id=f"{document_id}__chunk_{chunk.index:04d}",
                document_id=document_id,
                chunk_index=chunk.index,
                section_id=chunk.section_id,
                section_title=chunk.section_title,
                page_number=chunk.page_number,
                paragraph_ids=chunk.paragraph_ids,
                text=chunk.text,
                embedding=vec,
                model=f"{provider.name}:{provider.dimensions}",
            )
        )
    db.commit()


def _row_to_chunk(row: Embedding) -> Chunk:
    return Chunk(
        index=row.chunk_index,
        section_id=row.section_id,
        section_title=row.section_title,
        page_number=row.page_number,
        paragraph_ids=list(row.paragraph_ids or []),
        text=row.text,
    )


def retrieve(db: Session, document_id: str, query: str, *, top_k: int | None = None,
             section_id: str | None = None, page: int | None = None) -> list[RetrievedChunk]:
    """Semantic retrieval scoped to the whole paper, one section or one page."""
    s = get_settings()
    top_k = top_k or s.retrieval_top_k
    provider = get_embeddings()
    qvec = provider.embed_query(query)

    stmt = select(Embedding).where(Embedding.document_id == document_id)
    if section_id:
        stmt = stmt.where(Embedding.section_id == section_id)
    if page:
        stmt = stmt.where(Embedding.page_number.between(page - 1, page + 1))

    if s.is_postgres:
        stmt = stmt.order_by(Embedding.embedding.cosine_distance(qvec)).limit(top_k)
        rows = db.execute(stmt).scalars().all()
        # pgvector returns rows ordered by distance; recompute a score for the API.
        matrix = np.asarray([r.embedding for r in rows], dtype=np.float32) if rows else np.zeros((0, len(qvec)))
        scores = cosine_similarity(qvec, matrix) if rows else []
        return [RetrievedChunk(_row_to_chunk(r), float(sc)) for r, sc in zip(rows, scores)]

    rows = db.execute(stmt).scalars().all()
    if not rows:
        return []
    matrix = np.asarray([r.embedding or [0.0] * len(qvec) for r in rows], dtype=np.float32)
    scores = cosine_similarity(qvec, matrix)
    order = np.argsort(-scores)[:top_k]
    return [RetrievedChunk(_row_to_chunk(rows[i]), float(scores[i])) for i in order]
