import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.db import init_db
from backend.app.main import app
from sqlmodel import select
from backend.app.db import SessionLocal
from backend.app.models.embedding import Embedding
from backend.app.models.ticket import Ticket
from backend.app.schemas.ingest import IngestThread
from backend.app.services.findings import emit_ticket_draft, normalize_ingest_thread

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
    assert data["product_area"] == "account_access"
    assert data["severity"] == "high"
    assert "finding:authentication" in data["tags"]
    assert "Confidence: 1.00" in data["description"]

    # verify no feedback rows
    list_resp = client.get(f"/api/ticket-feedback/?ticket_id={data['id']}")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert rows == []

    # verify an embedding exists for the created ticket
    with SessionLocal() as session:
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
    assert ticket["product_area"] == "delivery_pipeline"
    assert ticket["severity"] == "high"
    assert "finding:build" in ticket["tags"]

    # verify feedback row exists
    list_resp = client.get(f"/api/ticket-feedback/?ticket_id={ticket['id']}")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert len(rows) == 1
    fb = rows[0]
    assert fb["helped"] is True
    assert payload["resolution_notes"] in fb["resolution_notes"]

    # verify embedding created for resolved ticket as well
    with SessionLocal() as session:
        tickets = session.exec(select(Ticket).where(Ticket.external_key == payload["external_id"])).all()
        assert len(tickets) >= 1
        t = tickets[-1]
        embeddings = session.exec(select(Embedding).where(Embedding.ticket_id == t.id)).all()
        assert len(embeddings) == 1
        assert embeddings[0].vector is not None


def test_normalize_and_emit_existing_sample_thread():
    sample_path = (
        Path("/home/runner/work/Echo-Help/Echo-Help/sample_data/sample_thread_slack.json")
    )
    payload = json.loads(sample_path.read_text())
    thread = IngestThread.model_validate(payload)

    finding = normalize_ingest_thread(thread)
    draft = emit_ticket_draft(finding)

    assert finding.finding_id == "slack:C12345:1710000000.0001"
    assert finding.category == "connectivity"
    assert finding.severity == "high"
    assert finding.status == "resolved"
    assert finding.product_area == "connectivity"
    assert finding.evidence[0] == payload["title"]
    assert draft.external_key == payload["external_id"]
    assert draft.status == "closed"
    assert draft.priority == "high"
    assert "Evidence:" in draft.description
