from fastapi.testclient import TestClient

from backend.app.main import app


def test_create_ticket_returns_created_ticket() -> None:
    payload = {
        "summary": "Printer keeps disconnecting",
        "description": "The office printer disconnects every 10 minutes.",
        "priority": "high",
    }

    with TestClient(app) as client:
        response = client.post("/api/tickets", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["summary"] == payload["summary"]
    assert body["description"] == payload["description"]
    assert body["status"] == "open"
    assert body["external_key"].startswith("ECHO-")


def test_create_ticket_rejects_short_summary() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/tickets",
            json={"summary": "a", "description": "valid description"},
        )

    assert response.status_code == 422
