from __future__ import annotations

import json
from datetime import datetime, timedelta

from backend.app.db import SessionLocal, init_db
from backend.app.models.ask_echo_feedback import AskEchoFeedback
from backend.app.models.ask_echo_log import AskEchoLog
from backend.app.models.ticket import Ticket
from backend.app.services.ranking_policy import rank_tickets


def test_learning_lite_signals_change_ordering() -> None:
    init_db()
    base = datetime(2026, 2, 1, 12, 0, 0)

    with SessionLocal() as session:
        t_bad_more_similar = Ticket(
            external_key="LP-BAD",
            source="test",
            project_key="TEST",
            summary="Login loop after SSO callback",
            description="Users are bounced after callback in prod with critical impact.",
            status="open",
            environment="stage",
            priority="P3",
            answer_quality_label="bad",
            fix_confirmed_good=False,
            tags=["severity:sev1", "fix_confirmed:false"],
            created_at=base,
            updated_at=base,
        )
        t_good_confirmed = Ticket(
            external_key="LP-MATCH",
            source="test",
            project_key="TEST",
            summary="Login loop after SSO callback",
            description="Users are bounced after callback.",
            status="closed",
            environment="prod",
            priority="P1",
            answer_quality_label="good",
            fix_confirmed_good=True,
            tags=["severity:sev1", "fix_confirmed:true"],
            created_at=base - timedelta(days=2),
            updated_at=base - timedelta(days=2),
            resolved_at=base - timedelta(days=1),
        )
        session.add(t_bad_more_similar)
        session.add(t_good_confirmed)
        session.commit()
        session.refresh(t_bad_more_similar)
        session.refresh(t_good_confirmed)

        semantic_scores = {
            int(t_bad_more_similar.id): 0.92,  # type: ignore[arg-type]
            int(t_good_confirmed.id): 0.78,  # type: ignore[arg-type]
        }

        baseline = rank_tickets(
            session,
            candidates=[t_bad_more_similar, t_good_confirmed],
            query="prod login loop critical",
            semantic_scores=semantic_scores,
            use_learning_lite=False,
        )
        weighted = rank_tickets(
            session,
            candidates=[t_bad_more_similar, t_good_confirmed],
            query="prod login loop critical",
            semantic_scores=semantic_scores,
            use_learning_lite=True,
        )

        assert baseline[0].ticket.external_key == "LP-BAD"
        assert weighted[0].ticket.external_key == "LP-MATCH"
        assert weighted[0].signals is not None
        assert weighted[0].signals.get("fix_confirmed") == 1.0
        assert weighted[0].signals.get("env_match") == 1.0
        assert weighted[1].signals is not None
        assert weighted[1].signals.get("bad_quality_penalty") == 1.0


def test_learning_lite_answer_feedback_boost_is_applied() -> None:
    init_db()
    base = datetime(2026, 2, 1, 12, 0, 0)

    with SessionLocal() as session:
        t_answer_helped = Ticket(
            external_key="LP-AF-YES",
            source="test",
            project_key="TEST",
            summary="SSO login loop in production",
            description="Users loop after callback in prod.",
            status="open",
            created_at=base,
            updated_at=base,
        )
        t_baseline = Ticket(
            external_key="LP-AF-NO",
            source="test",
            project_key="TEST",
            summary="SSO login loop in production",
            description="Users loop after callback in prod.",
            status="open",
            created_at=base,
            updated_at=base,
        )
        session.add(t_answer_helped)
        session.add(t_baseline)
        session.commit()
        session.refresh(t_answer_helped)
        session.refresh(t_baseline)

        assert t_answer_helped.id is not None
        assert t_baseline.id is not None

        baseline = rank_tickets(
            session,
            candidates=[t_answer_helped, t_baseline],
            query="sso login loop prod",
        )
        assert baseline[0].ticket.id == t_baseline.id

        log = AskEchoLog(
            query="sso login loop prod",
            mode="kb_answer",
            reasoning_notes=json.dumps(
                {
                    "features": {
                        "ticket": {
                            "signal_evidence": [{"ticket_id": int(t_answer_helped.id)}],
                        }
                    }
                }
            ),
        )
        session.add(log)
        session.commit()
        session.refresh(log)

        assert log.id is not None

        session.add(AskEchoFeedback(ask_echo_log_id=int(log.id), helped=True, notes="useful"))
        session.commit()

        weighted = rank_tickets(
            session,
            candidates=[t_answer_helped, t_baseline],
            query="sso login loop prod",
            use_learning_lite=True,
        )

        assert weighted[0].ticket.id == t_answer_helped.id
        assert weighted[0].signals is not None
        assert weighted[0].signals.get("answer_feedback") == 1.0
