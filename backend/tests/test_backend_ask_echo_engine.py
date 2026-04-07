from fastapi.testclient import TestClient

from backend.app.db import SessionLocal, init_db
from backend.app.main import app
from backend.app.services.ask_echo_engine import AskEchoEngine, AskEchoEngineRequest
from backend.app.services.llm_provider import ProviderAnswer, get_llm_provider
from backend.app.services.openai_provider import OpenAIProvider


class _StubProvider:
    def __init__(self, answer_text: str) -> None:
        self.answer_text = answer_text
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    def generate(self, problem: str, context: dict[str, object] | None = None) -> ProviderAnswer:
        self.calls.append((problem, context))
        return ProviderAnswer(answer_text=self.answer_text, mode="openai", confidence=0.8)


class _StubTicket:
    def __init__(self, ticket_id: int, summary: str, description: str) -> None:
        self.id = ticket_id
        self.summary = summary
        self.description = description


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


def test_ask_echo_route_preserves_public_contract() -> None:
    client = TestClient(app)

    response = client.post("/api/ask-echo", json={"q": "schema contract check", "limit": 2})
    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "kb_confidence" in data
    assert "reasoning" in data
    assert "evidence" in data


def test_get_llm_provider_requires_env_flag_and_key(monkeypatch) -> None:
    monkeypatch.delenv("ECHOHELP_OPENAI_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_llm_provider() is None

    monkeypatch.setenv("ECHOHELP_OPENAI_ENABLED", "true")
    assert get_llm_provider() is None

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = get_llm_provider()
    assert isinstance(provider, OpenAIProvider)


def test_ask_echo_engine_keeps_local_kb_answer_as_default() -> None:
    init_db()
    provider = _StubProvider("This should never replace the KB-backed answer.")
    engine = AskEchoEngine(
        ticket_retriever=lambda **_: [(0.91, _StubTicket(1, "Password reset loop", "Reset SSO session cache"))],
        snippet_retriever=lambda **_: [],
        llm_provider=provider,
    )

    with SessionLocal() as session:
        result = engine.run(session=session, req=AskEchoEngineRequest(query="password reset loop", limit=3))

    assert result.answer_kind == "grounded"
    assert result.mode == "kb_answer"
    assert provider.calls == []
    assert "Ticket #1" in result.response["answer"]


def test_ask_echo_engine_can_use_llm_provider_for_fallback_answers() -> None:
    init_db()
    provider = _StubProvider("Try re-authenticating the VPN client and clearing the cached token.")
    engine = AskEchoEngine(
        ticket_retriever=lambda **_: [],
        snippet_retriever=lambda **_: [],
        grounding_decider=lambda **_: False,
        llm_provider=provider,
    )

    with SessionLocal() as session:
        result = engine.run(session=session, req=AskEchoEngineRequest(query="vpn login keeps failing", limit=2))

    assert result.answer_kind == "ungrounded"
    assert result.mode == "general_answer"
    assert result.response["answer"].startswith("Try re-authenticating the VPN client")
    assert result.response["sources"] == []
    assert set(result.response.keys()) == {"answer", "confidence", "sources", "reasoning"}
    assert provider.calls == [
        (
            "vpn login keeps failing",
            {
                "local_answer": (
                    "I couldn't find any matching tickets or prior solutions in your history for this question. "
                    "Here's general guidance based on typical IT issues, but it's not specific to your environment."
                ),
                "sources": [],
                "mode": "general_answer",
            },
        )
    ]
