from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_feedback_records_contract_exposes_internal_analytics_shape() -> None:
    ask = client.post("/api/ask-echo", json={"q": "contract feedback records check", "limit": 3})
    assert ask.status_code == 200
    log_id = ask.json()["ask_echo_log_id"]

    feedback = client.post(
        "/api/ask-echo/feedback",
        json={"ask_echo_log_id": log_id, "helped": True, "notes": "useful"},
    )
    assert feedback.status_code == 200

    response = client.get("/api/ask-echo/feedback/records", params={"limit": 20})
    assert response.status_code == 200
    data = response.json()

    assert data["meta"]["kind"] == "ask_echo_feedback_records"
    assert data["meta"]["version"] == "v1"
    assert isinstance(data["items"], list)

    item = next(entry for entry in data["items"] if entry["ask_echo_log_id"] == log_id)
    assert isinstance(item["question"], str)
    assert isinstance(item["answer"], str)
    assert isinstance(item["confidence"], float)
    assert isinstance(item["source_count"], int)
    assert isinstance(item["sources"], list)
    assert isinstance(item["reasoning"], str)
    assert item["feedback_status"] == "helped"
    assert item["rating"] == 1
    assert item["feedback_notes"] == "useful"
    assert item["feedback_at"] is not None
    assert isinstance(item["low_confidence"], bool)
    assert isinstance(item["no_sources"], bool)
    assert isinstance(item["fallback_only"], bool)


def test_feedback_records_low_confidence_filter_only_returns_weak_answers() -> None:
    ask = client.post("/api/ask-echo", json={"q": "unlikely to match anything in backend history", "limit": 1})
    assert ask.status_code == 200
    log_id = ask.json()["ask_echo_log_id"]

    response = client.get("/api/ask-echo/feedback/records", params={"limit": 50, "low_confidence_only": True})
    assert response.status_code == 200
    data = response.json()

    filtered = [entry for entry in data["items"] if entry["ask_echo_log_id"] == log_id]
    assert len(filtered) == 1
    assert filtered[0]["low_confidence"] is True
    assert filtered[0]["no_sources"] is True
    assert filtered[0]["fallback_only"] is True
    assert filtered[0]["source_count"] == 0
    assert filtered[0]["sources"] == []
    assert filtered[0]["reasoning"].startswith("Fallback-only answer with no supporting sources.")


def test_log_detail_contract_surfaces_stable_display_fields() -> None:
    ask = client.post("/api/ask-echo", json={"q": "log detail contract check", "limit": 3})
    assert ask.status_code == 200
    log_id = ask.json()["ask_echo_log_id"]

    response = client.get(f"/api/ask-echo/logs/{log_id}")
    assert response.status_code == 200
    detail = response.json()

    assert detail["id"] == log_id
    assert isinstance(detail["query_text"], str)
    assert isinstance(detail["answer_text"], str)
    assert isinstance(detail["kb_confidence"], float)
    assert isinstance(detail["source_count"], int)
    assert detail["mode"] in ("kb_answer", "general_answer")
    assert detail["feedback_status"] in ("pending", "helped", "not_helped")
    assert isinstance(detail["low_confidence"], bool)
    assert isinstance(detail["no_sources"], bool)
    assert isinstance(detail["fallback_only"], bool)
    assert "reasoning" in detail
    assert isinstance(detail["reasoning"]["candidate_snippets"], list)
    assert isinstance(detail["reasoning"]["chosen_snippet_ids"], list)
