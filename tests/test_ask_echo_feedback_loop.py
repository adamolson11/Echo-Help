from fastapi.testclient import TestClient
from sqlmodel import select

from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models.ask_echo_feedback import AskEchoFeedback


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

    r3 = client.get("/api/ask-echo/feedback/summary", params={"days": 30})
    assert r3.status_code == 200
    summary = r3.json()
    assert summary.get("meta") is not None
    assert summary.get("window_days") == 30
    assert summary.get("total_feedback") >= 1
    assert summary.get("helped_false") >= 1
