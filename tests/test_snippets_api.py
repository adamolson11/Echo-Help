from fastapi.testclient import TestClient

from backend.app.db import init_db, SessionLocal
from backend.app.main import app
from sqlmodel import select
from backend.app.models.snippets import SolutionSnippet


client = TestClient(app)


def test_create_snippet_success():
    init_db()

    payload = {
        "title": "Fix VPN auth",
        "content_md": "Apply this patch to fix AUTH_FAILED in VPN client",
        "source": "test",
    }

    resp = client.post("/api/snippets/create", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["echo_score"] == 0.0

    # verify persisted
    sid = data["id"]
    with SessionLocal() as session:
        rows = session.exec(select(SolutionSnippet).where(SolutionSnippet.id == sid)).all()
        assert len(rows) == 1


def test_snippet_feedback_updates_counters_and_score():
    init_db()

    # create snippet
    payload = {"title": "Reset profile fix", "content_md": "Resetting profile fixed auth", "source": "test"}
    resp = client.post("/api/snippets/create", json=payload)
    assert resp.status_code == 200
    sdata = resp.json()
    sid = sdata["id"]

    # submit positive feedback
    fb = {"snippet_id": sid, "helped": True, "notes": "Worked for this user"}
    fbresp = client.post("/api/snippets/feedback", json=fb)
    assert fbresp.status_code == 200
    j = fbresp.json()
    assert j.get("snippet_id") == sid
    assert "echo_score" in j

    # verify counters in DB via session
    with SessionLocal() as session:
        rows = session.exec(select(SolutionSnippet).where(SolutionSnippet.id == sid)).all()
        assert len(rows) == 1
        snippet = rows[0]
        assert snippet.success_count >= 1


def test_snippet_search_returns_matching_results():
    init_db()

    # create two snippets
    client.post("/api/snippets/create", json={"title": "VPN auth fix", "content_md": "fix auth", "source": "test"})
    client.post("/api/snippets/create", json={"title": "Printer driver", "content_md": "install driver", "source": "test"})

    resp = client.get("/api/snippets/search", params={"q": "VPN", "limit": 5})
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    # expect at least one match and that titles contain VPN
    assert any((r.get("title") and ("vpn" in r.get("title").lower())) for r in results)


def test_snippet_search_empty_query_returns_empty():
    init_db()
    resp = client.get("/api/snippets/search", params={"q": "", "limit": 5})
    assert resp.status_code == 200
    results = resp.json()
    assert results == []


def test_feedback_unknown_snippet_returns_404():
    init_db()
    resp = client.post("/api/snippets/feedback", json={"snippet_id": 999999, "helped": True})
    assert resp.status_code == 404
    data = resp.json()
    assert data.get("detail") == "Snippet not found"


def test_feedback_requires_snippet_or_ticket():
    init_db()
    # missing both snippet_id and ticket_id should return 400
    resp = client.post("/api/snippets/feedback", json={"helped": True})
    assert resp.status_code == 400
    assert resp.json().get("detail") == "snippet_id or ticket_id required"


def test_feedback_accepts_optional_resolution_notes():
    init_db()
    # create snippet
    s = client.post("/api/snippets/create", json={"title": "Note test", "content_md": "do this", "source": "test"}).json()
    sid = s["id"]
    note = "This resolved the issue by restarting the agent"
    resp = client.post("/api/snippets/feedback", json={"snippet_id": sid, "helped": True, "notes": note})
    assert resp.status_code == 200

    # verify a feedback row persists with notes
    from sqlmodel import select
    from backend.app.db import SessionLocal
    from backend.app.models.snippets import SnippetFeedback

    with SessionLocal() as session:
        rows = session.exec(select(SnippetFeedback).where(SnippetFeedback.snippet_id == sid)).all()
        assert len(rows) >= 1
        assert any(r.notes and note in r.notes for r in rows)
