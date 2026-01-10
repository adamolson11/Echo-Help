from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from ..models.ticket_feedback import TicketFeedback


def get_feedback_patterns(session: Session, days: int = 30) -> dict:
    """Aggregate Ask Echo-style ticket feedback into a simple pattern view.

    This is intentionally lightweight and focuses on a few core stats that are
    cheap to compute and easy to explain. It does not perform any NLP or
    clustering; those can be layered on later via separate endpoints.
    """

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    feedback_rows: list[TicketFeedback] = list(
        session.exec(
            select(TicketFeedback).where(TicketFeedback.created_at >= cutoff)
        ).all()
    )

    total_feedback = len(feedback_rows)
    positive = 0
    negative = 0

    # Basic sentiment buckets using existing fields
    for fb in feedback_rows:
        # Prefer explicit rating if present; fall back to helped flag
        if fb.rating is not None:
            if fb.rating >= 4:
                positive += 1
            elif fb.rating <= 2:
                negative += 1
        else:
            if fb.helped is True:
                positive += 1
            elif fb.helped is False:
                negative += 1

    return {
        "stats": {
            "total_feedback": total_feedback,
            "positive": positive,
            "negative": negative,
            "window_days": days,
        },
        "top_comments": [],  # placeholder for future NLP / clustering
        "meta": {
            "kind": "feedback",
            "version": "v1",
        },
    }
