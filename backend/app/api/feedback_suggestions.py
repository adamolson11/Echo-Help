# ruff: noqa: B008
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlmodel import Session, select

from ..ai.normalize import normalize_phrase
from ..db import get_session
from ..models.ticket_feedback import TicketFeedback

router = APIRouter(tags=["feedback-suggestions"])


class FeedbackSuggestion(BaseModel):
    phrase: str
    count: int


@router.get(
    "/feedback-suggestions",
    response_model=list[FeedbackSuggestion],
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
            func.count(TicketFeedback.id).label("count"),  # type: ignore[reportArgumentType]
        )
        # SQLAlchemy expression APIs aren't fully visible to the type checker;
        # ignore the attribute-access diagnostics on these expressions.
        .where(TicketFeedback.resolution_notes.isnot(None))  # type: ignore[reportAttributeAccessIssue]
        .where(func.length(func.trim(TicketFeedback.resolution_notes)) > 0)  # type: ignore[reportUnknownMemberType]
        .group_by(TicketFeedback.resolution_notes)
        .order_by(func.count(TicketFeedback.id).desc())  # type: ignore[reportAttributeAccessIssue]
        .limit(limit)
    )

    # Defensive: check DB schema first. Some environments may not have the
    # `resolution_notes` column in the `ticketfeedback` table yet. Querying
    # that non-existent column results in an OperationalError on SQLite.
    try:
        # session.exec typing doesn't accept TextClause in stubs; narrow-ignore here.
        cols = session.exec(text("PRAGMA table_info('ticketfeedback')"))  # type: ignore[reportArgumentType]
        cols = cols.all()
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

    # Normalize phrases and aggregate counts for identical normalized phrases
    agg: dict[str, int] = {}
    for raw_phrase, cnt in rows:
        norm = normalize_phrase(raw_phrase or "")
        if not norm:
            continue
        agg[norm] = agg.get(norm, 0) + (cnt or 0)

    # Convert to sorted list of FeedbackSuggestion
    suggestions = [FeedbackSuggestion(phrase=ph, count=ct) for ph, ct in agg.items()]
    suggestions.sort(key=lambda s: s.count, reverse=True)
    # Respect the requested limit
    return suggestions[:limit]
