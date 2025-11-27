from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_search_empty_query():
    resp = client.post("/api/search", json={"q": ""})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
