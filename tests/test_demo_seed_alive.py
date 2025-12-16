from fastapi.testclient import TestClient

from backend.app.main import app
from scripts.seed_demo_org import seed_demo_org


def test_demo_seed_makes_ask_echo_alive():
    # Seed deterministic demo data into the per-test isolated DB.
    seed_demo_org()

    client = TestClient(app)
    resp = client.post("/api/ask-echo", json={"q": "password reset doesn't work", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("meta", {}).get("kind") == "ask_echo"
    assert data.get("query") == "password reset doesn't work"

    tickets = data.get("suggested_tickets")
    snippets = data.get("suggested_snippets")
    assert isinstance(tickets, list) and len(tickets) >= 1
    assert isinstance(snippets, list) and len(snippets) >= 1

    ticket_texts = [
        (t.get("title") or "") + " " + (t.get("summary") or "")
        for t in tickets
        if isinstance(t, dict)
    ]
    assert any("password reset" in s.lower() for s in ticket_texts)

    snippet_titles = [s.get("title", "") for s in snippets if isinstance(s, dict)]
    assert any("password reset" in s.lower() for s in snippet_titles)
