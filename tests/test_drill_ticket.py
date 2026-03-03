from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.ticket import Ticket
from backend.scripts.drill_ticket import render_drill


def _ticket_fixture() -> Ticket:
    now = datetime.now(UTC)
    return Ticket(
        external_key="ECHO-7777",
        source="seed",
        project_key="ECHO",
        summary="SSO callback loop in production",
        description="Users see redirect loop after callback.",
        status="closed",
        product_area="auth",
        environment="prod",
        owning_team="identity-platform",
        escalation_target="oncall-identity",
        severity="S1",
        priority="P0",
        repro_steps=["Open app", "Login via SSO", "Observe redirect loop"],
        expected_result="User lands on dashboard",
        actual_result="User bounces to login",
        resolution_good=["Align callback URI and nonce handling"],
        root_cause_good="Callback URI mismatch",
        resolution_bad=["Restarted auth service repeatedly"],
        bad_reason="Correlation not causation",
        created_at=now,
        updated_at=now,
        resolved_at=now,
    )


def test_drill_prompt_hides_resolution_fields() -> None:
    out = render_drill(_ticket_fixture(), mode="prompt", comments_limit=5)
    assert "REVEAL" not in out
    assert "Final fix:" not in out
    assert "Root cause:" not in out


def test_drill_reveal_includes_fix_and_did_not_work() -> None:
    out = render_drill(_ticket_fixture(), mode="reveal", comments_limit=5)
    assert "Final fix:" in out
    assert "[DID_NOT_WORK]" in out
    assert "identity-platform -> oncall-identity" in out
