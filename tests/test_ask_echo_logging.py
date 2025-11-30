import os
import tempfile

# Use a temp DB for this test
td = tempfile.NamedTemporaryFile(prefix="echohelp_test_", suffix=".db", delete=False)
td.close()
os.environ["ECHOHELP_DB_PATH"] = td.name

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.app.main import app
from backend.app.db import SessionLocal
from backend.app.models.ask_echo_log import AskEchoLog

client = TestClient(app)


def test_ask_echo_creates_log_entry():
    resp = client.post("/api/ask-echo", json={"q": "vpn auth_failed test", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("mode") in ("kb_answer", "general_answer")

    expected_query = "vpn auth_failed test"

    with SessionLocal() as session:
        rows = session.exec(select(AskEchoLog)).all()

    # At least one log should exist
    assert len(rows) >= 1

    # Ensure the specific query we just sent is present among logs
    assert any(getattr(log, "query", None) == expected_query for log in rows)
    # Also sanity-check that at least one matching row has the expected mode and references_count type
    matches = [log for log in rows if getattr(log, "query", None) == expected_query]
    assert any((getattr(m, "mode", None) in ("kb_answer", "general_answer") and isinstance(getattr(m, "references_count", None), int)) for m in matches)