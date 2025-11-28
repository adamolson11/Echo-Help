from fastapi import APIRouter, Depends
from sqlmodel import Session

from ...db import get_session
from ...services.patterns import get_feedback_patterns

router = APIRouter()


@router.get("/patterns/summary")
def patterns_summary(session: Session = Depends(get_session)) -> dict:
    return get_feedback_patterns(session)
