from fastapi.testclient import TestClient

from backend.app.main import app
from scripts.seed_demo_org import seed_demo_org


def test_machine_status_empty_db():
    client = TestClient(app)
    resp = client.get("/api/machine/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("meta") == {"kind": "machine_status", "version": "v1"}
    assert data.get("tickets_total") == 0
    assert data.get("snippets_total") == 0
    assert data.get("ask_echo_total") == 0
    assert data.get("feedback_total_30d") == 0
    assert data.get("ask_echo_ungrounded_rate_30d") == 0.0
    assert data.get("last_event_at") is None


def test_machine_status_after_demo_seed():
    seed_demo_org()

    client = TestClient(app)
    resp = client.get("/api/machine/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("meta") == {"kind": "machine_status", "version": "v1"}

    assert isinstance(data.get("tickets_total"), int) and data["tickets_total"] >= 10
    assert isinstance(data.get("snippets_total"), int) and data["snippets_total"] >= 5
    assert isinstance(data.get("ask_echo_total"), int) and data["ask_echo_total"] >= 1

    assert isinstance(data.get("feedback_total_30d"), int) and data["feedback_total_30d"] >= 1

    rate = data.get("ask_echo_ungrounded_rate_30d")
    assert isinstance(rate, float)
    assert 0.0 <= rate <= 1.0

    assert isinstance(data.get("last_event_at"), str)
    assert len(data["last_event_at"]) > 0
