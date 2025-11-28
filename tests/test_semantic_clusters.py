from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_semantic_clusters_smoke():
    resp = client.post("/api/insights/semantic-clusters", json={"n_clusters": 4, "max_examples": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # each cluster should have cluster_index and tickets
    if data:
        c = data[0]
        assert "cluster_index" in c
        assert "tickets" in c

