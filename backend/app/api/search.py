from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, or_
from ..db import get_session
from ..models import Ticket

router = APIRouter(tags=["search"])

@router.post("/search", response_model=List[Ticket])
def search_tickets(
    q: str,  # simple query string for now
    session: Session = Depends(get_session),
):
    """
    Very simple keyword search over summary and description.
    This will become semantic search later using embeddings.
    """
    if not q:
        return []
    stmt = select(Ticket).where(
        or_(
            Ticket.summary.ilike(f"%{q}%"),
            Ticket.description.ilike(f"%{q}%"),
        )
    )

    return session.exec(stmt).all()
