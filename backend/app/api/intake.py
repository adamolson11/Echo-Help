# ruff: noqa: B008
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..db import get_session
from ..schemas.intake import (IntakeRequest, IntakeResponse,
                              IntakeSuggestedTicket)
from ..services.semantic_search import semantic_search_tickets

router = APIRouter(tags=["intake"])


@router.post("/intake", response_model=IntakeResponse)
def intake_assistant(
    payload: IntakeRequest,
    session: Session = Depends(get_session),
):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    results = semantic_search_tickets(session, text, limit=10)

    suggested = []
    for score, t in results:
        # t.id is Optional[int] on the SQLModel type; skip items without ids.
        if t.id is None:
            continue
        suggested.append(
            IntakeSuggestedTicket(
                id=t.id,
                external_key=t.external_key,
                summary=t.summary,
                description=t.description,
                status=t.status,
                priority=t.priority,
                created_at=t.created_at,
                similarity=score,
            )
        )

    return IntakeResponse(
        query=text,
        suggested_tickets=suggested,
        predicted_category=None,
        predicted_subcategory=None,
    )
