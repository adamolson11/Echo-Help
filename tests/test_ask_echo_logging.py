from fastapi.testclient import TestClient
from sqlmodel import select

from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models.ask_echo_log import AskEchoLog

client = TestClient(app)


def test_ask_echo_creates_log_entry():
    resp = client.post("/api/ask-echo", json={"q": "vpn auth_failed test", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("mode") in ("kb_answer", "general_answer")
    assert isinstance(data.get("ask_echo_log_id"), int)

    expected_query = "vpn auth_failed test"

    with SessionLocal() as session:
        rows = session.exec(select(AskEchoLog)).all()

    # At least one log should exist
    assert len(rows) >= 1

    # Ensure the specific query we just sent is present among logs
    assert any(getattr(log, "query", None) == expected_query for log in rows)
    # Also sanity-check that at least one matching row has the expected mode and references_count type
    matches = [log for log in rows if getattr(log, "query", None) == expected_query]
    assert any(
        (
            getattr(m, "mode", None) in ("kb_answer", "general_answer")
            and isinstance(getattr(m, "references_count", None), int)
            and isinstance(getattr(m, "answer_text", None), str)
            and isinstance(getattr(m, "source_count", None), int)
            and isinstance(getattr(m, "feedback_rating", None), int)
            and getattr(m, "feedback_status", None) == "pending"
        )
        for m in matches
    )


def test_ask_echo_logs_low_confidence_state_for_fallback_answers():
    resp = client.post("/api/ask-echo", json={"q": "no matching backend history expected", "limit": 3})
    assert resp.status_code == 200
    log_id = resp.json().get("ask_echo_log_id")
    assert isinstance(log_id, int)

    with SessionLocal() as session:
        log = session.get(AskEchoLog, log_id)
        assert log is not None
        assert log.low_confidence is True
        assert log.no_sources is True
        assert log.fallback_only is True
        assert isinstance(log.reasoning_summary, str)
        assert "Fallback-only answer" in log.reasoning_summary
