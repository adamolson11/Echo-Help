from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from backend.app.db import SessionLocal, init_db
from backend.app.main import app
from backend.app.models.ticket import Ticket
from backend.app.models.ticket_feedback import TicketFeedback
from backend.app.services.ranking_policy import rank_tickets


def _make_ticket(*, external_key: str, summary: str, created_at: datetime) -> Ticket:
    return Ticket(
        external_key=external_key,
        source="test",
        project_key="TEST",
        summary=summary,
        description=summary,
        status="open",
        created_at=created_at,
        updated_at=created_at,
    )


def test_rank_tickets_deterministic_across_input_orders():
    init_db()
    base = datetime(2025, 1, 10, 12, 0, 0)

    with SessionLocal() as session:
        t_new = _make_ticket(external_key="T-NEW", summary="VPN is down", created_at=base)
        t_old = _make_ticket(external_key="T-OLD", summary="VPN is down", created_at=base - timedelta(days=2))
        session.add(t_new)
        session.add(t_old)
        session.commit()
        session.refresh(t_new)
        session.refresh(t_old)

        r1 = rank_tickets(session, candidates=[t_new, t_old], query="vpn")
        r2 = rank_tickets(session, candidates=[t_old, t_new], query="vpn")

        assert [rt.ticket.id for rt in r1] == [rt.ticket.id for rt in r2]
        assert [rt.ticket.id for rt in r1][:2] == [t_new.id, t_old.id]


def test_rank_tickets_feedback_can_change_rank():
    init_db()
    base = datetime(2025, 1, 10, 12, 0, 0)

    with SessionLocal() as session:
        t_a = _make_ticket(external_key="T-A", summary="MFA enrollment broken", created_at=base)
        t_b = _make_ticket(external_key="T-B", summary="MFA enrollment broken", created_at=base)
        session.add(t_a)
        session.add(t_b)
        session.commit()
        session.refresh(t_a)
        session.refresh(t_b)

        assert t_b.id is not None

        # Add explicit positive feedback to t_b.
        fb = TicketFeedback(ticket_id=int(t_b.id), query_text="mfa", rating=1, helped=True)
        session.add(fb)
        session.commit()

        ranked = rank_tickets(session, candidates=[t_a, t_b], query="mfa")
        assert ranked[0].ticket.id == t_b.id


def test_search_endpoint_uses_ranking_policy_ordering():
    init_db()

    with SessionLocal() as session:
        base = datetime(2025, 1, 10, 12, 0, 0)
        t_a = _make_ticket(external_key="S-A", summary="Password reset loop", created_at=base)
        t_b = _make_ticket(external_key="S-B", summary="Password reset loop", created_at=base)
        session.add(t_a)
        session.add(t_b)
        session.commit()
        session.refresh(t_a)
        session.refresh(t_b)

        assert t_b.id is not None

        # Make t_b clearly preferred by ranking policy.
        session.add(TicketFeedback(ticket_id=int(t_b.id), query_text="password reset", rating=1, helped=True))
        session.commit()

    client = TestClient(app)
    resp = client.post("/api/search", json={"q": "password reset"})
    assert resp.status_code == 200
    ids = [row["id"] for row in resp.json()]
    assert ids[0] == t_b.id
