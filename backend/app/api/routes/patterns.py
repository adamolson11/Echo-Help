from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from ...db import get_session
from ...schemas.patterns import FeedbackPatternsSummary
from ...services.patterns import get_feedback_patterns

router = APIRouter()


@router.get("/patterns/summary", response_model=FeedbackPatternsSummary)
def patterns_summary(
    days: int = Query(30, ge=1, le=365),
    session: Session = Depends(get_session),
) -> dict:
    """Return a lightweight summary of Ask Echo ticket feedback patterns.

    This endpoint is intentionally simple and read-only. It reports how many
    feedback events were seen in the last ``days`` days, and a coarse
    positive/negative breakdown. It is designed to be cheap to compute and
    stable over time.
    """

    return get_feedback_patterns(session, days=days)
