from fastapi.testclient import TestClient

from backend.app.db import init_db
from backend.app.main import app
from sqlmodel import Session, select
from backend.app.db import engine
from backend.app.models.embedding import Embedding
from backend.app.models.ticket import Ticket

client = TestClient(app)


def test_unresolved_thread_creates_ticket_only():
    init_db()

    payload = {
        "source": "slack",
        "external_id": "SLACK-1234",
        "title": "Help with login",
        "resolved": False,
        "messages": [
            {"author": "alice", "text": "I can't log in"},
            {"author": "bob", "text": "Have you tried resetting your password?"},
        ],
    }

    resp = client.post("/api/ingest/thread", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["summary"] == payload["title"]
    assert data["status"] == "open"

    # verify no feedback rows
    list_resp = client.get(f"/api/ticket-feedback/?ticket_id={data['id']}")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert rows == []

    # verify an embedding exists for the created ticket
    with Session(engine) as session:
        tickets = session.exec(select(Ticket).where(Ticket.external_key == payload["external_id"])).all()
        assert len(tickets) >= 1
        t = tickets[-1]
        embeddings = session.exec(select(Embedding).where(Embedding.ticket_id == t.id)).all()
        assert len(embeddings) == 1
        assert embeddings[0].vector is not None


def test_resolved_thread_creates_ticket_and_feedback():
    init_db()

    payload = {
        "source": "jira",
        "external_id": "JIRA-999",
        "title": "Error on build server",
        "resolved": True,
        "resolution_notes": "Fixed by restarting the worker",
        "messages": [{"author": "ci", "text": "build failed: timeout"}],
    }

    resp = client.post("/api/ingest/thread", json=payload)
    assert resp.status_code == 200, resp.text
    ticket = resp.json()
    assert ticket["status"] == "closed"

    # verify feedback row exists
    list_resp = client.get(f"/api/ticket-feedback/?ticket_id={ticket['id']}")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert len(rows) == 1
    fb = rows[0]
    assert fb["helped"] is True
    assert payload["resolution_notes"] in fb["resolution_notes"]

    # verify embedding created for resolved ticket as well
    with Session(engine) as session:
        tickets = session.exec(select(Ticket).where(Ticket.external_key == payload["external_id"])).all()
        assert len(tickets) >= 1
        t = tickets[-1]
        embeddings = session.exec(select(Embedding).where(Embedding.ticket_id == t.id)).all()
        assert len(embeddings) == 1
        assert embeddings[0].vector is not None
