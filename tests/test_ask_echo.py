from fastapi.testclient import TestClient

from backend.app.main import app


def test_ask_echo_requires_query():
    client = TestClient(app)
    resp = client.post("/api/ask-echo", json={"q": ""})
    assert resp.status_code == 400


def test_ask_echo_empty_results():
    client = TestClient(app)
    resp = client.post("/api/ask-echo", json={"q": "some question", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("meta") is not None
    assert data.get("ask_echo_log_id") is not None
    assert data.get("answer_kind") in ("grounded", "ungrounded")
    assert data.get("query") == "some question"
    assert "answer" in data
    assert isinstance(data.get("suggested_tickets"), list)
    assert isinstance(data.get("suggested_snippets"), list)
