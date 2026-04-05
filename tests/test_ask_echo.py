from fastapi.testclient import TestClient
from datetime import UTC, datetime

from backend.app.db import SessionLocal
from backend.app.models.kb_entry import KBEntry
from backend.app.models.ticket import Ticket

from backend.app.main import app


def test_ask_echo_requires_query():
    client = TestClient(app)
    resp = client.post("/api/ask-echo", json={"q": ""})
    assert resp.status_code == 400
    data = resp.json()
    assert isinstance(data, dict)
    assert isinstance(data.get("detail"), str)


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
    assert isinstance(data.get("flywheel"), dict)
    assert data["flywheel"].get("issue") == "some question"
    assert data["flywheel"].get("state", {}).get("current_stage") == "recommendations_ready"
    assert len(data["flywheel"].get("recommendations", [])) == 3
    assert data["flywheel"].get("outcome_options") == [
        "resolved",
        "partially_resolved",
        "not_resolved",
        "needs_escalation",
    ]


def test_ask_echo_includes_kb_evidence_when_kb_present() -> None:
    with SessionLocal() as session:
        now = datetime.now(UTC)
        session.add(
            KBEntry(
                entry_id="KB-ASK-1",
                title="How to configure auth callback",
                body_markdown="Use setup steps and callback verification checks.",
                tags=["auth", "how to", "setup"],
                product_area="auth",
                source_system="seed_kb",
                updated_at=now,
            )
        )
        session.add(
            Ticket(
                external_key="ECHO-ASK-KB-1",
                source="seed",
                project_key="ECHO",
                summary="Auth callback setup problem",
                description="Need setup instructions for callback flow",
                status="open",
                product_area="auth",
                environment="prod",
                priority="P1",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    client = TestClient(app)
    resp = client.post("/api/ask-echo", json={"q": "how do I setup auth callback", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("kb_evidence"), list)
    assert len(data["kb_evidence"]) >= 1
    assert data["kb_evidence"][0].get("entry_id")
    assert len(data.get("flywheel", {}).get("recommendations", [])) == 3
