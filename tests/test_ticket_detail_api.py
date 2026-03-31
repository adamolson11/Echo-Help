from fastapi.testclient import TestClient

from backend.app.main import app


def test_get_ticket_by_id_returns_full_ticket() -> None:
    with TestClient(app) as client:
        tickets_response = client.get("/api/tickets")
        assert tickets_response.status_code == 200
        tickets = tickets_response.json()
        assert tickets

        ticket_id = tickets[0]["id"]
        detail_response = client.get(f"/api/tickets/{ticket_id}")

        assert detail_response.status_code == 200
        payload = detail_response.json()
        assert payload["id"] == ticket_id
        assert payload["summary"]
        assert "description" in payload


def test_get_ticket_by_id_returns_404_for_unknown_ticket() -> None:
    with TestClient(app) as client:
        response = client.get("/api/tickets/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"