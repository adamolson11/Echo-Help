from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db import init_db

client = TestClient(app)


def test_ask_echo_returns_snippets_field_and_ordering():
    init_db()

    # use a unique token so we only match created snippets in this test
    import uuid
    token = f"UT-{uuid.uuid4().hex[:8]}"

    s1 = client.post("/api/snippets/create", json={"title": f"Disk full fix {token}", "content_md": "cleanup /var/log", "source": "test"}).json()
    s2 = client.post("/api/snippets/create", json={"title": f"Auth token refresh {token}", "content_md": "rotate tokens", "source": "test"}).json()
    s3 = client.post("/api/snippets/create", json={"title": f"VPN auth fix {token}", "content_md": "update certs", "source": "test"}).json()

    # give feedback: make s3 high score, s2 medium, s1 low
    client.post("/api/snippets/feedback", json={"snippet_id": s3["id"], "helped": True})
    client.post("/api/snippets/feedback", json={"snippet_id": s3["id"], "helped": True})
    client.post("/api/snippets/feedback", json={"snippet_id": s2["id"], "helped": True})
    client.post("/api/snippets/feedback", json={"snippet_id": s1["id"], "helped": False})

    # ask a query that should match the unique token
    resp = client.post("/api/ask-echo", json={"q": token, "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "snippets" in data
    snippets = data["snippets"]
    assert isinstance(snippets, list)
    # Expect the highest scoring snippet (s3) to appear first among returned snippets
    ids = [s["id"] for s in snippets]
    assert s3["id"] in ids
    # If multiple snippets returned, ensure order by echo_score descending
    if len(snippets) >= 2:
        scores = [s.get("echo_score", 0) for s in snippets]
        assert scores == sorted(scores, reverse=True)


def test_ask_echo_handles_no_snippets_and_no_tickets():
    init_db()
    resp = client.post("/api/ask-echo", json={"q": "no-such-query", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("query") == "no-such-query"
    assert "snippets" in data
    assert data["snippets"] == []
