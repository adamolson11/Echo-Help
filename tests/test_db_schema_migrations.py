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


def test_init_db_migrates_ticketfeedback_missing_columns() -> None:
    """Regression: existing DBs may have ticketfeedback missing newer columns.

    The ticket feedback model grew columns like `helped` and `resolution_notes`.
    Older DBs can break inserts if those columns are missing.
    """

    db_path = os.getenv("ECHOHELP_DB_PATH")
    assert db_path, "test isolation fixture should set ECHOHELP_DB_PATH"

    # Create an old-schema ticketfeedback table missing helped/resolution_notes.
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ticketfeedback (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER NOT NULL,
            query_text TEXT NOT NULL,
            rating INTEGER NOT NULL,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    init_db()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(ticketfeedback)")
    cols = {r[1] for r in cur.fetchall()}
    conn.close()

    assert "helped" in cols
    assert "resolution_notes" in cols
    assert "ai_cluster_id" in cols
    assert "ai_summary" in cols

    # And the endpoint should be able to insert.
    client = TestClient(app)
    r = client.post(
        "/api/ticket-feedback/",
        json={
            "ticket_id": 1,
            "query_text": "schema drift feedback",
            "rating": 5,
            "helped": True,
            "resolution_notes": "reset password",
        },
    )
    assert r.status_code == 200
