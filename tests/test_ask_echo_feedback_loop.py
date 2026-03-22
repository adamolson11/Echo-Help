from fastapi.testclient import TestClient
from sqlmodel import select

from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models.ask_echo_feedback import AskEchoFeedback
from backend.app.models.ask_echo_log import AskEchoLog


def test_ask_echo_feedback_round_trip() -> None:
    client = TestClient(app)

    r = client.post("/api/ask-echo", json={"q": "ungrounded question for feedback", "limit": 3})
    assert r.status_code == 200
    data = r.json()
    log_id = data.get("ask_echo_log_id")
    assert isinstance(log_id, int)

    r2 = client.post(
        "/api/ask-echo/feedback",
        json={"ask_echo_log_id": log_id, "helped": False, "notes": "did not help"},
    )
    assert r2.status_code == 200
    saved = r2.json()
    assert saved.get("ask_echo_log_id") == log_id
    assert saved.get("helped") is False

    with SessionLocal() as session:
        rows = session.exec(select(AskEchoFeedback).where(AskEchoFeedback.ask_echo_log_id == log_id)).all()
        assert len(rows) == 1
        log = session.get(AskEchoLog, log_id)
        assert log is not None
        assert log.feedback_status == "not_helped"
        assert log.feedback_rating == -1

    r3 = client.get("/api/ask-echo/feedback/summary", params={"days": 30})
    assert r3.status_code == 200
    summary = r3.json()
    assert summary.get("meta") is not None
    assert summary.get("window_days") == 30
    assert summary.get("total_feedback") >= 1
    assert summary.get("helped_false") >= 1

    r4 = client.get("/api/ask-echo/feedback/records", params={"limit": 10})
    assert r4.status_code == 200
    records = r4.json()
    assert records.get("meta", {}).get("kind") == "ask_echo_feedback_records"
    assert isinstance(records.get("items"), list)
    matching = [item for item in records["items"] if item.get("ask_echo_log_id") == log_id]
    assert len(matching) == 1
    assert matching[0].get("rating") == -1
    assert matching[0].get("feedback_status") == "not_helped"
    assert isinstance(matching[0].get("question"), str)
    assert isinstance(matching[0].get("answer"), str)
    assert isinstance(matching[0].get("confidence"), float)
    assert isinstance(matching[0].get("source_count"), int)
