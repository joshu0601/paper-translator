from app.database import SessionLocal
from app.models import Document, Paragraph, Section, Translation
from app.services import pipeline


def test_translate_handles_duplicate_paragraphs(client):
    """Repeated text (running footers, licence lines) must not violate the
    translation-cache UNIQUE constraint (regression)."""
    db = SessionLocal()
    doc = Document(title="dup", file_name="dup.pdf", storage_key="dup/dup.pdf", page_count=2, steps=pipeline.initial_steps())
    db.add(doc)
    db.flush()
    sec = Section(id=f"{doc.id}__section_01", document_id=doc.id, title="Body", kind="other", order=0, start_page=1)
    db.add(sec)
    db.flush()
    footer = "Do not consider usage charge for this document."
    texts = [footer, "A real paragraph about reinforcement learning.", footer, footer, "Another paragraph."]
    for i, t in enumerate(texts, 1):
        db.add(Paragraph(id=f"{doc.id}__paragraph_{i:04d}", document_id=doc.id, section_id=sec.id, page_number=1, original_text=t, order=i, kind="paragraph"))
    db.commit()

    pipeline.translate_document(db, doc, pipeline.StepReporter(db, doc))

    rows = db.query(Paragraph).filter(Paragraph.document_id == doc.id).order_by(Paragraph.order).all()
    assert all(p.translated_text for p in rows)
    assert rows[0].translated_text == rows[2].translated_text == rows[3].translated_text
    from app.services.text import sha256

    assert db.query(Translation).filter(Translation.source_hash == sha256(footer)).count() == 1
    assert next(s for s in doc.steps if s["key"] == "translate")["status"] == "done"
    db.delete(doc)
    db.commit()
    db.close()
