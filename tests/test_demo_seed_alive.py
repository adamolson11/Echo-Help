from fastapi.testclient import TestClient
from sqlmodel import select

from backend.app.main import app
from backend.app.db import SessionLocal
from backend.app.models.snippets import SolutionSnippet
from backend.app.models.ticket import Ticket
from scripts.seed_demo_org import seed_demo_org


def _assert_alive_for_query(client: TestClient, *, q: str, expected_token: str) -> None:
    resp = client.post("/api/ask-echo", json={"q": q, "limit": 5})
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("meta", {}).get("kind") == "ask_echo"
    assert data.get("query") == q

    tickets = data.get("suggested_tickets")
    snippets = data.get("suggested_snippets")
    assert isinstance(tickets, list) and len(tickets) >= 1
    assert isinstance(snippets, list) and len(snippets) >= 1

    token = expected_token.lower()

    ticket_texts = [
        (t.get("title") or "") + " " + (t.get("summary") or "")
        for t in tickets
        if isinstance(t, dict)
    ]
    assert any(token in s.lower() for s in ticket_texts)

    snippet_titles = [s.get("title", "") for s in snippets if isinstance(s, dict)]
    assert any(token in s.lower() for s in snippet_titles)


def test_demo_seed_makes_ask_echo_alive_signature_queries():
    # Seed deterministic demo data into the per-test isolated DB.
    seed_demo_org()
    client = TestClient(app)

    # Keep it lightweight (2–3 queries) but ensure the primary is covered.
    _assert_alive_for_query(
        client,
        q="password reset doesn't work",
        expected_token="password reset",
    )
    _assert_alive_for_query(client, q="vpn auth_failed", expected_token="vpn")
    _assert_alive_for_query(client, q="mfa codes invalid", expected_token="mfa")


def test_demo_seed_is_idempotent():
    seed_demo_org()
    seed_demo_org()

    with SessionLocal() as session:
        demo_tickets = list(session.exec(select(Ticket).where(Ticket.source == "demo")).all())
        assert len(demo_tickets) >= 10
        external_keys = [t.external_key for t in demo_tickets]
        assert len(external_keys) == len(set(external_keys))

        demo_snippets = list(
            session.exec(select(SolutionSnippet).where(SolutionSnippet.source == "demo")).all()
        )
        assert len(demo_snippets) >= 5
        snippet_keys = [(s.title, s.source) for s in demo_snippets]
        assert len(snippet_keys) == len(set(snippet_keys))
