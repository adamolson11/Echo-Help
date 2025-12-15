from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from backend.app.db import SessionLocal, init_db
from backend.app.main import app
from backend.app.models.ticket_feedback import TicketFeedback


client = TestClient(app)


def _seed_feedback() -> None:
    init_db()
    now = datetime.utcnow()
    with SessionLocal() as session:
        # Ensure a clean slate so these tests don't leak state
        session.query(TicketFeedback).delete()
        rows = [
            TicketFeedback(ticket_id=1, query_text="foo", rating=5, helped=True),
            TicketFeedback(ticket_id=2, query_text="bar", rating=1, helped=False),
            TicketFeedback(ticket_id=3, query_text="baz", rating=4, helped=True),
        ]
        for r in rows:
            r.created_at = now - timedelta(days=1)
            session.add(r)
        session.commit()


def test_feedback_patterns_summary_smoke() -> None:
    _seed_feedback()

    resp = client.get("/api/patterns/summary?days=30")
    assert resp.status_code == 200
    data = resp.json()

    assert "stats" in data
    assert "meta" in data
    assert data["meta"]["kind"] == "feedback"
    assert data["meta"]["version"] == "v1"

    stats = data["stats"]
    assert stats["window_days"] == 30
    assert isinstance(stats["total_feedback"], int)
    assert isinstance(stats["positive"], int)
    assert isinstance(stats["negative"], int)


def test_feedback_patterns_counts_match_seed_data() -> None:
    _seed_feedback()

    resp = client.get("/api/patterns/summary?days=30")
    assert resp.status_code == 200
    data = resp.json()

    stats = data["stats"]
    # We seeded three feedback rows: two effectively positive (5, 4) and one negative (1)
    assert stats["total_feedback"] >= 3
    assert stats["positive"] >= 2
    assert stats["negative"] >= 1
