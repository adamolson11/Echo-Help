from __future__ import annotations

# ruff: noqa: B008
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from ...db import get_session
from ...models.ask_echo_feedback import AskEchoFeedback
from ...models.ask_echo_log import AskEchoLog
from ...models.snippets import SnippetFeedback, SolutionSnippet
from ...models.ticket import Ticket
from ...models.ticket_feedback import TicketFeedback
from ...schemas.machine import MachineStatusResponse

router = APIRouter(tags=["machine"])


def _count(session: Session, model) -> int:
    stmt = select(func.count()).select_from(model)
    val = session.exec(stmt).one()
    return int(val or 0)


def _count_since(session: Session, model, *, cutoff: datetime) -> int:
    stmt = select(func.count()).select_from(model).where(model.created_at >= cutoff)  # type: ignore[attr-defined]
    val = session.exec(stmt).one()
    return int(val or 0)


def _max_created_at(session: Session, model) -> datetime | None:
    stmt = select(func.max(model.created_at))  # type: ignore[attr-defined]
    return session.exec(stmt).one()


@router.get("/machine/status", response_model=MachineStatusResponse)
def get_machine_status(session: Session = Depends(get_session)) -> MachineStatusResponse:
    now = datetime.now(timezone.utc)
    cutoff_30d = now - timedelta(days=30)

    tickets_total = _count(session, Ticket)
    snippets_total = _count(session, SolutionSnippet)
    ask_echo_total = _count(session, AskEchoLog)

    ask_echo_30d_total = _count_since(session, AskEchoLog, cutoff=cutoff_30d)
    ask_echo_ungrounded_30d = int(
        session.exec(
            select(func.count())
            .select_from(AskEchoLog)
            .where(
                AskEchoLog.created_at >= cutoff_30d,
                AskEchoLog.mode == "general_answer",
            )
        ).one()
        or 0
    )

    ask_echo_ungrounded_rate_30d = (
        float(ask_echo_ungrounded_30d) / float(ask_echo_30d_total)
        if ask_echo_30d_total > 0
        else 0.0
    )

    feedback_total_30d = (
        _count_since(session, TicketFeedback, cutoff=cutoff_30d)
        + _count_since(session, SnippetFeedback, cutoff=cutoff_30d)
        + _count_since(session, AskEchoFeedback, cutoff=cutoff_30d)
    )

    last_event_at = max(
        [
            d
            for d in [
                _max_created_at(session, Ticket),
                _max_created_at(session, SolutionSnippet),
                _max_created_at(session, AskEchoLog),
                _max_created_at(session, TicketFeedback),
                _max_created_at(session, SnippetFeedback),
                _max_created_at(session, AskEchoFeedback),
            ]
            if d is not None
        ],
        default=None,
    )

    return MachineStatusResponse(
        tickets_total=tickets_total,
        snippets_total=snippets_total,
        ask_echo_total=ask_echo_total,
        ask_echo_ungrounded_rate_30d=ask_echo_ungrounded_rate_30d,
        feedback_total_30d=feedback_total_30d,
        last_event_at=last_event_at,
    )
