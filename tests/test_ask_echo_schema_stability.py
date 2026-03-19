from fastapi.testclient import TestClient

from backend.app.main import app


def test_ask_echo_response_schema_stability() -> None:
    client = TestClient(app)

    resp = client.post("/api/ask-echo", json={"q": "schema stability check", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()

    # Meta envelope must always exist and remain versioned.
    meta = data.get("meta")
    assert isinstance(meta, dict)
    assert isinstance(meta.get("kind"), str)
    assert isinstance(meta.get("version"), str)
    assert meta.get("kind") == "ask_echo"
    assert meta.get("version") == "v2"

    # Core contract fields.
    assert data.get("answer_kind") in ("grounded", "ungrounded")
    assert isinstance(data.get("ask_echo_log_id"), int)
    assert isinstance(data.get("kb_confidence"), float)
    assert data.get("mode") in ("kb_answer", "general_answer")

    # Arrays should always be present (possibly empty).
    assert isinstance(data.get("references"), list)
    assert isinstance(data.get("suggested_tickets"), list)
    assert isinstance(data.get("suggested_snippets"), list)

    # Internal analytics fields must stay off the public response.
    assert "feedback_status" not in data
    assert "low_confidence" not in data
    assert "source_count" not in data

    # If we got any ticket summaries, they must have stable keys.
    if len(data["suggested_tickets"]) > 0:
        first = data["suggested_tickets"][0]
        assert isinstance(first, dict)
        assert isinstance(first.get("id"), int)
