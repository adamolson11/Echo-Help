from __future__ import annotations

# ruff: noqa: B008
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ...db import get_session
from ...models.ticket_feedback import TicketFeedback
from ...schemas.ticket_feedback import (
    TicketFeedbackCreate,
    TicketFeedbackRead,
)

router = APIRouter(
    prefix="/ticket-feedback",
    tags=["ticket-feedback"],
)


@router.post("/", response_model=TicketFeedbackRead)
def create_ticket_feedback(
    payload: TicketFeedbackCreate,
    session: Session = Depends(get_session),
) -> TicketFeedbackRead:
    feedback = TicketFeedback.model_validate(payload)
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    # Convert ORM -> read schema so the response_type matches exactly.
    return TicketFeedbackRead.model_validate(feedback)


@router.get("/", response_model=list[TicketFeedbackRead])
def list_ticket_feedback(
    ticket_id: int | None = None,
    session: Session = Depends(get_session),
) -> list[TicketFeedbackRead]:
    query = select(TicketFeedback)
    if ticket_id is not None:
        query = query.where(TicketFeedback.ticket_id == ticket_id)

    results = session.exec(query).all()
    # Return a list of read models (convert ORM objects to read schema)
    return [TicketFeedbackRead.model_validate(r) for r in results]
