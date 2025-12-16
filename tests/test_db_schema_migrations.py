import os
import sqlite3

from fastapi.testclient import TestClient

from backend.app.db import init_db
from backend.app.main import app


def test_init_db_migrates_askecholog_missing_columns(monkeypatch):
    """Regression: existing DBs may have askecholog missing newer columns.

    We create an old-schema askecholog table (no reasoning/audit fields), run
    init_db(), then ensure Ask Echo can write a log without SQLITE errors.
    """

    db_path = os.getenv("ECHOHELP_DB_PATH")
    assert db_path, "test isolation fixture should set ECHOHELP_DB_PATH"

    # Create an old-schema askecholog table (missing candidate_snippet_ids_json, etc.).
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS askecholog (
            id INTEGER PRIMARY KEY,
            query TEXT NOT NULL,
            top_score REAL NOT NULL DEFAULT 0.0,
            kb_confidence REAL NOT NULL DEFAULT 0.0,
            mode TEXT NOT NULL,
            references_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    # init_db should add missing columns on existing askecholog.
    init_db()

    # Verify columns exist.
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(askecholog)")
    cols = {r[1] for r in cur.fetchall()}
    conn.close()

    assert "candidate_snippet_ids_json" in cols
    assert "chosen_snippet_ids_json" in cols
    assert "echo_score" in cols
    assert "reasoning_notes" in cols

    # And Ask Echo should work (no 500 from log insert).
    client = TestClient(app)
    r = client.post("/api/ask-echo", json={"q": "schema drift check", "limit": 3})
    assert r.status_code == 200
