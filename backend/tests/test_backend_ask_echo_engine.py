from fastapi.testclient import TestClient

from backend.app.db import SessionLocal, init_db
from backend.app.main import app
from backend.app.services.ask_echo_engine import AskEchoEngine, AskEchoEngineRequest
from backend.app.services.llm_provider import ProviderAnswer, get_configured_llm_provider


def test_ask_echo_engine_response_schema_is_always_present() -> None:
    init_db()

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


def test_ask_echo_engine_provider_seam_preserves_public_schema() -> None:
    init_db()

    class RecordingProvider:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object]]] = []

        def generate(self, problem: str, context: dict[str, object]) -> ProviderAnswer:
            self.calls.append((problem, context))
            return ProviderAnswer(answer_text="Provider answer from seam.", mode="openai")

    provider = RecordingProvider()
    engine = AskEchoEngine(
        ticket_retriever=lambda **_: [],
        snippet_retriever=lambda **_: [],
        grounding_decider=lambda **_: False,
        llm_provider=provider,
    )

    with SessionLocal() as session:
        result = engine.run(session=session, req=AskEchoEngineRequest(query="provider seam check", limit=2))

    assert len(provider.calls) == 1
    assert provider.calls[0][0] == "provider seam check"
    assert provider.calls[0][1]["local_answer"]
    assert set(result.response.keys()) == {"answer", "confidence", "sources", "reasoning"}
    assert result.answer_kind == "ungrounded"
    assert result.mode == "general_answer"
    assert result.answer_text.startswith("Provider answer from seam.")
    assert result.response["sources"] == []


def test_openai_provider_factory_is_env_gated(monkeypatch) -> None:
    monkeypatch.delenv("ECHOHELP_OPENAI_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_configured_llm_provider() is None

    monkeypatch.setenv("ECHOHELP_OPENAI_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    provider = get_configured_llm_provider()

    assert provider is not None
    assert provider.__class__.__name__ == "OpenAIProvider"


def test_ask_echo_route_preserves_public_contract() -> None:
    client = TestClient(app)

    response = client.post("/api/ask-echo", json={"q": "schema contract check", "limit": 2})
    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "kb_confidence" in data
    assert "reasoning" in data
    assert "evidence" in data
