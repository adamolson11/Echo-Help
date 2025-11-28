from fastapi.testclient import TestClient

from backend.app.db import init_db, engine
from backend.app.main import app
from sqlmodel import Session, select
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
    with Session(engine) as session:
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
    with Session(engine) as session:
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
