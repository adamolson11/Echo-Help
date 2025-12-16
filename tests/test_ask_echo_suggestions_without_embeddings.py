from fastapi.testclient import TestClient

from backend.app.db import get_session, init_db
from backend.app.main import app
from backend.app.models.ticket import Ticket


def test_ask_echo_returns_suggested_tickets_without_embeddings() -> None:
    """Regression: Ask Echo should still suggest tickets when embeddings are absent.

    "Absent" here means: no embedding rows exist for tickets.
    """

    init_db()

    token = "NOEMB-REG"

    with next(get_session()) as session:
        t = Ticket(
            external_key=f"T-{token}",
            source="test",
            project_key="IT",
            summary=f"VPN login broken {token}",
            description="User sees auth error when connecting",
            status="open",
            priority="medium",
        )
        session.add(t)
        session.commit()
        session.refresh(t)
        ticket_id = t.id

    client = TestClient(app)
    resp = client.post("/api/ask-echo", json={"q": token, "limit": 5})
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data.get("suggested_tickets"), list)
    ids = [item.get("id") for item in data["suggested_tickets"]]
    assert ticket_id in ids
