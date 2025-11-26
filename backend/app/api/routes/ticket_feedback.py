from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.app.db import get_session
from backend.app.models.ticket_feedback import TicketFeedback
from backend.app.schemas.ticket_feedback import (
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
    return feedback


@router.get("/", response_model=List[TicketFeedbackRead])
def list_ticket_feedback(
    ticket_id: Optional[int] = None,
    session: Session = Depends(get_session),
) -> list[TicketFeedbackRead]:
    query = select(TicketFeedback)
    if ticket_id is not None:
        query = query.where(TicketFeedback.ticket_id == ticket_id)

    results = session.exec(query).all()
    return results