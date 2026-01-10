# ruff: noqa: B008
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ..db import get_session
from ..models import Ticket, TicketFeedback


class FeedbackRequest(BaseModel):
    ticket_id: int
    query_text: str
    rating: int


class FeedbackResponse(BaseModel):
    id: int
    ticket_id: int
    rating: int


router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackRequest,
    session: Session = Depends(get_session),
):
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=400, detail="rating must be 1–5")

    ticket = session.get(Ticket, payload.ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")

    # Map incoming feedback to stored TicketFeedback fields.
    # We store the user's free-text under `resolution_notes` and map
    # a numeric `rating` to the boolean `helped` field (>=4 => helped).
    fb = TicketFeedback(
        ticket_id=payload.ticket_id,
        query_text=payload.query_text.strip(),
        rating=payload.rating,
        resolution_notes=payload.query_text.strip(),
        helped=(payload.rating >= 4),
    )
    session.add(fb)
    session.commit()
    session.refresh(fb)

    # fb.id is Optional[int] at type-level but will be set after commit/refresh.
    assert fb.id is not None

    return FeedbackResponse(
        id=fb.id,
        ticket_id=fb.ticket_id,
        rating=payload.rating,
    )
