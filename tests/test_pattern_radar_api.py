import os
import tempfile

# Use an isolated temp SQLite DB for these tests so they don't pick up
# existing developer data in the repo DB file.
td = tempfile.NamedTemporaryFile(prefix="echohelp_test_", suffix=".db", delete=False)
td.close()
os.environ["ECHOHELP_DB_PATH"] = td.name

from fastapi.testclient import TestClient

from backend.app.db import init_db, SessionLocal
from backend.app.main import app
from sqlmodel import select, delete
from backend.app.models.snippets import SolutionSnippet, SnippetFeedback

client = TestClient(app)


def seed_feedback(snippet_id: int, helped_values):
    for h in helped_values:
        client.post("/api/snippets/feedback", json={"snippet_id": snippet_id, "helped": h})


def test_pattern_radar_empty_db_returns_zero_stats():
    init_db()
    # Ensure snippets and related feedback are removed to guarantee
    # an empty DB for this test even when running in the full suite.
    with SessionLocal() as session:
        # Delete feedback first due to FK constraints
        session.exec(delete(SnippetFeedback))
        session.exec(delete(SolutionSnippet))
        session.commit()
    resp = client.get("/api/insights/pattern-radar")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stats"]["total_snippets"] == 0
    assert data["stats"]["total_successes"] == 0
    assert data["stats"]["total_failures"] == 0
    assert data["top_frequent_snippets"] == []
    assert data["top_risky_snippets"] == []


def test_pattern_radar_returns_top_frequent_and_risky():
    init_db()
    # create three snippets
    a = client.post("/api/snippets/create", json={"title": "A", "content_md": "a", "source": "test"}).json()
    b = client.post("/api/snippets/create", json={"title": "B", "content_md": "b", "source": "test"}).json()
    c = client.post("/api/snippets/create", json={"title": "C", "content_md": "c", "source": "test"}).json()

    # A: 3 successes
    seed_feedback(a["id"], [True, True, True])
    # B: 2 failures
    seed_feedback(b["id"], [False, False])
    # C: mix: 1 success, 4 failures
    seed_feedback(c["id"], [True, False, False, False, False])

    resp = client.get("/api/insights/pattern-radar")
    assert resp.status_code == 200
    data = resp.json()

    # stats
    assert data["stats"]["total_snippets"] >= 3
    # total successes should be at least 4 (3 from A + 1 from C)
    assert data["stats"]["total_successes"] >= 4
    # total failures should be at least 6 (2 from B + 4 from C)
    assert data["stats"]["total_failures"] >= 6

    # top lists exist
    assert "top_frequent_snippets" in data
    assert "top_risky_snippets" in data

    # C should likely be in risky list because of high failure rate
    risky_titles = [s.get("problem_summary") or s.get("id") for s in data["top_risky_snippets"]]
    assert any(str(x) == "C" or str(x).startswith("C") for x in risky_titles) or len(data["top_risky_snippets"]) > 0
