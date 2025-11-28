from fastapi.testclient import TestClient

from backend.app.db import init_db
from backend.app.main import app

client = TestClient(app)


def test_ticket_feedback_round_trip():
    # Make sure tables exist
    init_db()

    payload = {
        "ticket_id": 99999,
        "rating": 4,
        "resolution_notes": "Cleared cache and retried login",
        "query_text": "login cache issue",
        "helped": True,
    }

    resp = client.post("/api/ticket-feedback/", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ticket_id"] == 99999
    assert data["rating"] == 4
    assert data["resolution_notes"].startswith("Cleared cache")

    # verify record is retrievable
    list_resp = client.get(f"/api/ticket-feedback/?ticket_id={payload['ticket_id']}")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert any(r["resolution_notes"].startswith("Cleared cache") for r in rows)
