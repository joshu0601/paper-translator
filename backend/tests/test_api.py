import time

import pytest


@pytest.fixture(scope="module")
def ready_document(client):
    res = client.post("/api/documents/demo")
    assert res.status_code == 201
    doc = res.json()
    for _ in range(240):
        doc = client.get(f"/api/documents/{doc['id']}").json()
        if doc["status"] in ("ready", "failed"):
            break
        time.sleep(0.25)
    assert doc["status"] == "ready", doc.get("error")
    return doc


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["llm"] == "mock"


def test_cors_allows_lan_origins(client):
    for origin in ("http://192.168.10.166:3000", "http://10.0.0.5:3000", "http://localhost:3000"):
        res = client.options(
            "/api/documents",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )
        assert res.status_code == 200, origin
        assert res.headers.get("access-control-allow-origin") == origin
    res = client.options(
        "/api/documents",
        headers={"Origin": "http://evil.example.com", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in res.headers


def test_upload_rejects_non_pdf(client):
    res = client.post("/api/documents/upload", files={"file": ("x.txt", b"hello", "text/plain")})
    assert res.status_code == 400


def test_document_pipeline(client, ready_document):
    doc = ready_document
    assert all(s["status"] == "done" for s in doc["steps"])
    assert doc["pageCount"] >= 3
    assert doc["authors"]

    sections = client.get(f"/api/documents/{doc['id']}/sections").json()
    assert [s["kind"] for s in sections][:2] == ["abstract", "introduction"]

    paragraphs = client.get(f"/api/documents/{doc['id']}/paragraphs").json()
    assert paragraphs[0]["id"].endswith("paragraph_0001")
    prose = [p for p in paragraphs if p["kind"] == "paragraph"]
    assert all(p["translatedText"] for p in prose)

    figures = client.get(f"/api/documents/{doc['id']}/figures").json()
    assert figures and client.get(figures[0]["imageUrl"]).status_code == 200
    assert client.get(f"/api/documents/{doc['id']}/file").status_code == 200


def test_chat_returns_valid_citations(client, ready_document):
    doc_id = ready_document["id"]
    res = client.post(f"/api/documents/{doc_id}/chat", json={"message": "Reward Function 是什麼？", "context": "entire_document"})
    assert res.status_code == 200
    body = res.json()
    assert body["sessionId"] and body["answer"]
    assert body["citations"], "answer must be traceable"
    paragraph_ids = {p["id"] for p in client.get(f"/api/documents/{doc_id}/paragraphs").json()}
    for c in body["citations"]:
        assert c["paragraphId"] in paragraph_ids
    assert any("reward" in c["snippet"].lower() for c in body["citations"])

    # Follow-up in the same session and a scoped context mode.
    sections = client.get(f"/api/documents/{doc_id}/sections").json()
    intro = next(s for s in sections if s["kind"] == "introduction")
    res = client.post(
        f"/api/documents/{doc_id}/chat",
        json={"message": "主要 Contribution 是什麼？", "context": "current_section", "sectionId": intro["id"], "sessionId": body["sessionId"]},
    )
    assert res.status_code == 200
    assert res.json()["sessionId"] == body["sessionId"]
    assert all(c["section"].endswith("Introduction") for c in res.json()["citations"])


def test_search(client, ready_document):
    doc_id = ready_document["id"]
    exact = client.post(f"/api/documents/{doc_id}/search", json={"query": "reward function", "type": "exact"}).json()
    assert exact and all("reward function" in r["preview"].lower() for r in exact)
    semantic = client.post(f"/api/documents/{doc_id}/search", json={"query": "how is the reward designed?", "type": "semantic"}).json()
    assert semantic and semantic[0]["score"] >= semantic[-1]["score"]


def test_notes_and_highlights(client, ready_document):
    doc_id = ready_document["id"]
    pid = client.get(f"/api/documents/{doc_id}/paragraphs").json()[1]["id"]

    note = client.post(f"/api/documents/{doc_id}/notes", json={"paragraphId": pid, "content": "remember this", "selectedText": "MEC"})
    assert note.status_code == 201
    assert len(client.get(f"/api/documents/{doc_id}/notes").json()) == 1
    assert client.delete(f"/api/notes/{note.json()['id']}").status_code == 204

    bad = client.post(f"/api/documents/{doc_id}/highlights", json={"paragraphId": pid, "selectedText": "x", "startOffset": 5, "endOffset": 2})
    assert bad.status_code == 400
    hl = client.post(f"/api/documents/{doc_id}/highlights", json={"paragraphId": pid, "selectedText": "Mobile", "startOffset": 0, "endOffset": 6})
    assert hl.status_code == 201
    assert client.delete(f"/api/highlights/{hl.json()['id']}").status_code == 204


def test_summary(client, ready_document):
    doc_id = ready_document["id"]
    res = client.get(f"/api/documents/{doc_id}/summary?length=short")
    assert res.status_code == 200 and res.json()["content"]
    again = client.get(f"/api/documents/{doc_id}/summary?length=short").json()
    assert again["createdAt"] == res.json()["createdAt"]  # cached


def test_delete_document(client, ready_document):
    doc_id = ready_document["id"]
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    assert client.get(f"/api/documents/{doc_id}").status_code == 404
