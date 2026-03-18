from fastapi.testclient import TestClient

from backend.app.db import SessionLocal, init_db
from backend.app.main import app
from backend.app.services.ask_echo_engine import AskEchoEngine, AskEchoEngineRequest
from backend.app.services.feedback import clear_recorded_feedback, list_recorded_feedback


def test_ask_echo_engine_response_schema_is_always_present() -> None:
    init_db()
    clear_recorded_feedback()

    engine = AskEchoEngine(
        ticket_retriever=lambda **_: [],
        snippet_retriever=lambda **_: [],
    )

    with SessionLocal() as session:
        result = engine.run(session=session, req=AskEchoEngineRequest(query="reset my password", limit=3))

    response = result.response
    assert set(response.keys()) == {"answer", "confidence", "sources", "reasoning"}
    assert isinstance(response["answer"], str)
    assert isinstance(response["confidence"], float)
    assert 0.0 <= response["confidence"] <= 1.0
    assert isinstance(response["sources"], list)
    assert isinstance(response["reasoning"], str)
    assert result.answer_text == response["answer"]
    assert result.kb_confidence == response["confidence"]

    recorded = list_recorded_feedback()
    assert recorded[-1]["question"] == "reset my password"
    assert recorded[-1]["answer"] == response["answer"]
    assert recorded[-1]["rating"] == 0


def test_ask_echo_engine_fallback_response_has_empty_sources() -> None:
    init_db()

    engine = AskEchoEngine(
        ticket_retriever=lambda **_: [],
        snippet_retriever=lambda **_: [],
        grounding_decider=lambda **_: False,
    )

    with SessionLocal() as session:
        result = engine.run(session=session, req=AskEchoEngineRequest(query="no matching history", limit=2))

    assert result.answer_kind == "ungrounded"
    assert result.response["sources"] == []
    assert result.response["confidence"] == 0.0
    assert "Fallback answer" in result.response["reasoning"]


def test_ask_echo_route_preserves_public_contract() -> None:
    client = TestClient(app)

    response = client.post("/api/ask-echo", json={"q": "schema contract check", "limit": 2})
    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "kb_confidence" in data
    assert "reasoning" in data
    assert "evidence" in data
