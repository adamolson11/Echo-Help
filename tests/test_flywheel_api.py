from fastapi.testclient import TestClient
from sqlmodel import select

from backend.app.api.routes import flywheel as flywheel_route
from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models.ask_echo_feedback import AskEchoFeedback
from backend.app.models.ask_echo_log import AskEchoLog
from backend.app.models.ticket_feedback import TicketFeedback
from backend.app.schemas.ask_echo import AskEchoReasoning
from backend.app.services.ask_echo_engine import AskEchoEngineResult
from backend.app.services.provider_seam import ProviderAnswer


def test_flywheel_recommend_returns_three_actions() -> None:
    client = TestClient(app)

    resp = client.post("/api/flywheel/recommend", json={"problem": "vpn auth_failed on macbook after reset"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["meta"]["kind"] == "flywheel_plan"
    assert data["issue"]["problem"] == "vpn auth_failed on macbook after reset"
    assert isinstance(data["issue"]["ask_echo_log_id"], int)
    assert len(data["recommendations"]) == 3
    assert [item["id"] for item in data["recommendations"]] == [
        "apply-grounded-fix",
        "compare-similar-case",
        "capture-learning",
    ]
    assert all(len(item["steps"]) == 3 for item in data["recommendations"])
    assert data["states"][1]["id"] == "recommend"
    assert data["states"][1]["status"] == "current"


def test_flywheel_outcome_persists_feedback() -> None:
    client = TestClient(app)

    recommend = client.post("/api/flywheel/recommend", json={"problem": "mfa reset blocked after phone swap"})
    assert recommend.status_code == 200, recommend.text
    plan = recommend.json()
    selected = plan["recommendations"][0]
    ask_echo_log_id = plan["issue"]["ask_echo_log_id"]

    outcome = client.post(
        "/api/flywheel/outcome",
        json={
            "ask_echo_log_id": ask_echo_log_id,
            "problem": plan["issue"]["problem"],
            "recommendation_id": selected["id"],
            "recommendation_title": selected["title"],
            "ticket_id": 424242,
            "outcome_status": "resolved",
            "completed_step_ids": [step["id"] for step in selected["steps"][:2]],
            "execution_notes": "Followed the top grounded path and confirmed login success.",
            "reusable_learning": "Phone swap issues should start with MFA rebind verification.",
        },
    )
    assert outcome.status_code == 200, outcome.text
    saved = outcome.json()
    assert saved["meta"]["kind"] == "flywheel_outcome"
    assert saved["saved"]["helped"] is True
    assert isinstance(saved["saved"]["ask_echo_feedback_id"], int)
    assert isinstance(saved["saved"]["ticket_feedback_id"], int)
    assert saved["saved"]["learning_summary"] == "Phone swap issues should start with MFA rebind verification."

    with SessionLocal() as session:
        log = session.get(AskEchoLog, ask_echo_log_id)
        assert log is not None
        assert log.feedback_status == "helped"
        assert log.feedback_rating == 1

        ask_feedback = session.exec(
            select(AskEchoFeedback).where(AskEchoFeedback.ask_echo_log_id == ask_echo_log_id)
        ).all()
        assert ask_feedback
        assert "Reusable learning" in (ask_feedback[-1].notes or "")

        ticket_feedback = session.exec(
            select(TicketFeedback).where(TicketFeedback.ticket_id == 424242)
        ).all()
        assert ticket_feedback
        assert "MFA rebind verification" in (ticket_feedback[-1].resolution_notes or "")


def test_flywheel_recommend_provider_fallback_preserves_contract(monkeypatch) -> None:
    client = TestClient(app)

    fake_result = AskEchoEngineResult(
        response={
            "answer": "Local fallback answer",
            "confidence": 0.2,
            "sources": [],
            "reasoning": "Fallback answer because no strong KB-backed match was available.",
        },
        answer_kind="ungrounded",
        mode="general_answer",
        kb_backed=False,
        top_ticket_score=0.0,
        references=[],
        reasoning=AskEchoReasoning(candidate_snippets=[], chosen_snippet_ids=[], echo_score=None),
        ticket_summaries=[],
        snippet_summaries=[],
        features={
            "version": "v1",
            "ticket": {"count": 0, "top_score": 0.0, "signal_evidence": []},
            "snippet": {"count": 0, "top_echo_score": 0.0, "top_success_count": 0, "top_failure_count": 0},
        },
        evidence=[],
        kb_evidence=[],
    )

    class FakeProvider:
        def generate(self, problem: str, context) -> ProviderAnswer | None:
            return ProviderAnswer(
                answer_text="Provider-guided next step with the same flywheel contract.",
                mode="provider_openai",
            )

    def fake_run(*args, **kwargs):
        return fake_result

    monkeypatch.setattr(flywheel_route.AskEchoEngine, "run", fake_run)
    monkeypatch.setattr(flywheel_route, "build_llm_provider_from_env", lambda: FakeProvider())

    resp = client.post("/api/flywheel/recommend", json={"problem": "new outage with no local match"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["meta"]["kind"] == "flywheel_plan"
    assert data["issue"]["mode"] == "provider_openai"
    assert data["issue"]["answer"] == "Provider-guided next step with the same flywheel contract."
    assert len(data["recommendations"]) == 3
    assert all(len(item["steps"]) == 3 for item in data["recommendations"])
