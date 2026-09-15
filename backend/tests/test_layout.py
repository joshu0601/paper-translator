import pymupdf

from app.services.layout import split_translation


def test_split_translation_prefers_sentence_boundaries():
    text = "第一句話很短。第二句話比較長一點，裡面還有逗號。第三句話結束了。"
    pieces = split_translation(text, [10, 10, 10])
    assert len(pieces) == 3
    assert "".join(pieces) == text.replace(" ", "")
    assert all(p.endswith("。") for p in pieces[:2])


def test_split_translation_single_box_is_identity():
    assert split_translation("abc", [5]) == ["abc"]


def test_page_endpoints_and_translated_pdf(client):
    import time

    doc = client.post("/api/documents/demo").json()
    for _ in range(240):
        doc = client.get(f"/api/documents/{doc['id']}").json()
        if doc["status"] in ("ready", "failed"):
            break
        time.sleep(0.25)
    assert doc["status"] == "ready", doc.get("error")
    assert next(s for s in doc["steps"] if s["key"] == "layout")["status"] == "done"

    pages = client.get(f"/api/documents/{doc['id']}/pages").json()
    assert len(pages) == doc["pageCount"] and pages[0]["width"] > 0

    paragraphs = client.get(f"/api/documents/{doc['id']}/paragraphs").json()
    assert all(p["boxes"] for p in paragraphs if p["kind"] == "paragraph")

    orig = client.get(pages[0]["originalUrl"])
    assert orig.status_code == 200 and orig.headers["content-type"] == "image/png"
    zh = client.get(pages[0]["translatedUrl"])
    assert zh.status_code == 200 and zh.headers["content-type"] == "image/png"

    pdf = client.get(f"/api/documents/{doc['id']}/translated.pdf")
    assert pdf.status_code == 200
    with pymupdf.open(stream=pdf.content, filetype="pdf") as d:
        assert d.page_count == doc["pageCount"]
        text = d[0].get_text()
        assert "模擬翻譯" not in text  # marker stripped
        # The abstract block was replaced by the (mock) translation, figures kept.
        assert "（延遲）" in text
        assert any(len(p.get_images()) >= 1 for p in d)

    client.delete(f"/api/documents/{doc['id']}")
