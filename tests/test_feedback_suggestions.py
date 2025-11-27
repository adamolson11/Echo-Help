from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_feedback_suggestions_endpoint():
    resp = client.get("/api/feedback-suggestions?limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
