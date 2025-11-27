from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import func, text

from ..db import get_session
from ..models.ticket_feedback import TicketFeedback

router = APIRouter(tags=["feedback-suggestions"])


class FeedbackSuggestion(BaseModel):
    phrase: str
    count: int


@router.get(
    "/feedback-suggestions",
    response_model=List[FeedbackSuggestion],
    summary="Most common actual fix phrases from ticket feedback",
)
def get_feedback_suggestions(
    limit: int = 50,
    session: Session = Depends(get_session),
):
    """
    Group `TicketFeedback.resolution_notes` phrases and return the most common ones.
    """

    stmt = (
        select(
            TicketFeedback.resolution_notes,
            func.count(TicketFeedback.id).label("count"),
        )
        .where(TicketFeedback.resolution_notes.isnot(None))
        .where(func.length(func.trim(TicketFeedback.resolution_notes)) > 0)
        .group_by(TicketFeedback.resolution_notes)
        .order_by(func.count(TicketFeedback.id).desc())
        .limit(limit)
    )

    # Defensive: check DB schema first. Some environments may not have the
    # `resolution_notes` column in the `ticketfeedback` table yet. Querying
    # that non-existent column results in an OperationalError on SQLite.
    try:
        cols = session.exec(text("PRAGMA table_info('ticketfeedback')")).all()
    except Exception:
        # If this fails for any reason, don't crash the endpoint.
        return []

    # PRAGMA table_info returns rows like (cid, name, type, notnull, dflt_value, pk)
    col_names = [row[1] for row in cols]
    if "resolution_notes" not in col_names:
        return []

    try:
        rows = session.exec(stmt).all()
    except Exception as exc:  # pragma: no cover - runtime DB may still fail
        print("feedback-suggestions query error:", exc)
        return []

    return [
        FeedbackSuggestion(phrase=row[0], count=row[1]) for row in rows
    ]
