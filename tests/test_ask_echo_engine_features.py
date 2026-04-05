from backend.app.db import SessionLocal, init_db
from backend.app.models.ticket import Ticket
from backend.app.services.ask_echo_engine import (
    AskEchoEngine,
    AskEchoEngineRequest,
    build_ask_echo_features,
)
from backend.app.services.llm_provider import ProviderAnswer


class _StubSnippet:
    def __init__(self, echo_score: float | None, success_count: int = 0, failure_count: int = 0):
        self.echo_score = echo_score
        self.success_count = success_count
        self.failure_count = failure_count


def test_build_ask_echo_features_shape() -> None:
    feats = build_ask_echo_features(scored_tickets=[(0.7, object()), (0.2, object())], snippets=[_StubSnippet(0.9, 3, 1)])
    assert feats["version"] == "v1"
    assert feats["ticket"]["count"] == 2
    assert feats["ticket"]["top_score"] == 0.7
    assert feats["snippet"]["count"] == 1
    assert feats["snippet"]["top_echo_score"] == 0.9
    assert feats["snippet"]["top_success_count"] == 3
    assert feats["snippet"]["top_failure_count"] == 1


def test_build_ask_echo_features_empty() -> None:
    feats = build_ask_echo_features(scored_tickets=[], snippets=[])
    assert feats["ticket"]["count"] == 0
    assert feats["ticket"]["top_score"] == 0.0
    assert feats["snippet"]["count"] == 0
    assert feats["snippet"]["top_echo_score"] == 0.0


class _TrackingProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def generate(self, *, problem: str, context: dict[str, object]) -> ProviderAnswer:
        self.calls.append((problem, context))
        return ProviderAnswer(
            answer_text="Check the failing edge first, then document the exact escalation trigger.",
            mode="openai_fallback",
            confidence=0.42,
            sources=[],
        )


def test_ask_echo_engine_uses_provider_only_for_fallback_answers() -> None:
    init_db()
    provider = _TrackingProvider()
    engine = AskEchoEngine(
        ticket_retriever=lambda **_: [],
        snippet_retriever=lambda **_: [],
        grounding_decider=lambda **_: False,
        llm_provider=provider,
    )

    with SessionLocal() as session:
        result = engine.run(
            session=session,
            req=AskEchoEngineRequest(query="provider seam fallback regression token", limit=3),
        )

    assert len(provider.calls) == 1
    assert result.mode == "general_answer"
    assert result.response["sources"] == []
    assert result.response["answer"].startswith(
        "Check the failing edge first, then document the exact escalation trigger."
    )
    assert len(result.flywheel.recommendations) == 3
    assert result.features["provider"]["used"] is True
    assert result.features["provider"]["mode"] == "openai_fallback"


def test_ask_echo_engine_keeps_local_grounded_answers_without_provider_call() -> None:
    init_db()
    provider = _TrackingProvider()
    ticket = Ticket(
        external_key="ECO-LOCAL-1",
        source="test",
        project_key="IT",
        summary="VPN login fix",
        description="Reset the cached credential and retry.",
        status="open",
    )
    ticket.id = 101
    engine = AskEchoEngine(
        ticket_retriever=lambda **_: [(0.91, ticket)],
        snippet_retriever=lambda **_: [],
        grounding_decider=lambda **_: True,
        llm_provider=provider,
    )

    with SessionLocal() as session:
        result = engine.run(
            session=session,
            req=AskEchoEngineRequest(query="vpn auth failed", limit=3),
        )

    assert provider.calls == []
    assert result.mode == "kb_answer"
    assert result.features["provider"]["used"] is False
    assert result.response["answer"].startswith("Based on your past tickets")
