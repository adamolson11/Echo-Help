from datetime import datetime, timedelta

from backend.app.db import SessionLocal, init_db
from backend.app.main import app
from backend.app.models.ticket import Ticket
from fastapi.testclient import TestClient


client = TestClient(app)


def test_ticket_pattern_radar_endpoint_smoke() -> None:
    resp = client.get("/api/insights/ticket-pattern-radar?days=14")
    assert resp.status_code == 200
    data = resp.json()
    assert "top_keywords" in data
    assert "frequent_titles" in data
    assert "semantic_clusters" in data
    assert "stats" in data
    assert "total_tickets" in data["stats"]
    assert "window_days" in data["stats"]


def test_ticket_pattern_radar_counts_match_inserted_tickets() -> None:
    # Ensure DB is initialized
    init_db()

    # Insert a few recent tickets with overlapping words
    with SessionLocal() as session:
        now = datetime.utcnow()
        tickets = [
            Ticket(
                external_key="VPN-1",
                source="test",
                project_key="TEST",
                summary="VPN not working",
                description="vpn timeout error",
                status="open",
            ),
            Ticket(
                external_key="VPN-2",
                source="test",
                project_key="TEST",
                summary="VPN timeout",
                description="vpn connection timeout",
                status="open",
            ),
            Ticket(
                external_key="EMAIL-1",
                source="test",
                project_key="TEST",
                summary="Email issues",
                description="email not sending",
                status="open",
            ),
        ]
        for t in tickets:
            t.created_at = now - timedelta(days=1)
            session.add(t)
        session.commit()

    resp = client.get("/api/insights/ticket-pattern-radar?days=30")
    assert resp.status_code == 200
    data = resp.json()

    stats = data["stats"]
    assert isinstance(stats["total_tickets"], int)
    assert stats["window_days"] == 30

    # Counts in lists should be positive integers when present
    for item in data["top_keywords"]:
        assert isinstance(item["count"], int)
        assert item["count"] >= 1

    for item in data["frequent_titles"]:
        assert isinstance(item["count"], int)
        assert item["count"] >= 1
