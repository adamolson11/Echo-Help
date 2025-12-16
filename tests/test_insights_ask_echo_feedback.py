from fastapi.testclient import TestClient

from backend.app.main import app


def test_insights_ask_echo_feedback_smoke() -> None:
    client = TestClient(app)

    # Create a log + feedback row
    r = client.post("/api/ask-echo", json={"q": "insights ask-echo feedback", "limit": 3})
    assert r.status_code == 200
    log_id = r.json().get("ask_echo_log_id")
    assert isinstance(log_id, int)

    r2 = client.post(
        "/api/ask-echo/feedback",
        json={"ask_echo_log_id": log_id, "helped": True, "notes": "worked"},
    )
    assert r2.status_code == 200

    r3 = client.get("/api/insights/ask-echo-feedback", params={"limit": 10})
    assert r3.status_code == 200
    data = r3.json()

    assert isinstance(data.get("meta"), dict)
    assert data["meta"].get("kind") == "ask_echo_feedback"
    assert isinstance(data.get("items"), list)
    assert len(data["items"]) >= 1

    first = data["items"][0]
    assert isinstance(first.get("id"), int)
    assert isinstance(first.get("ask_echo_log_id"), int)
    assert isinstance(first.get("helped"), bool)
    assert "query_text" in first
    assert "notes" in first
    assert "created_at" in first
