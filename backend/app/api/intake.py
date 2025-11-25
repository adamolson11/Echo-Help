from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..db import get_session
from ..services.semantic_search import semantic_search_tickets
from ..schemas.intake import IntakeRequest, IntakeResponse, IntakeSuggestedTicket

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

    suggested = [
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
        for score, t in results
    ]

    return IntakeResponse(
        query=text,
        suggested_tickets=suggested,
        predicted_category=None,
        predicted_subcategory=None,
    )
