from fastapi.testclient import TestClient

from backend.app.main import app


def test_create_ticket_persists_and_returns_detail() -> None:
    payload = {
        "summary": "Customer cannot finish MFA enrollment",
        "description": "Enrollment fails after QR scan with a generic retry message.",
        "priority": "high",
    }

    with TestClient(app) as client:
        create_response = client.post("/api/tickets", json=payload)

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["summary"] == payload["summary"]
        assert created["description"] == payload["description"]
        assert created["status"] == "open"
        assert created["source"] == "manual"
        assert created["project_key"] == "IT"
        assert created["external_key"].startswith("E-TKT-")
        assert created["short_id"] == created["external_key"]

        detail_response = client.get(f"/api/tickets/{created['id']}")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == created["id"]
    assert detail["summary"] == payload["summary"]