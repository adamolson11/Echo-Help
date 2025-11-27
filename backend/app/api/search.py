from typing import List

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from sqlmodel import Session, select, or_
from ..db import get_session
from ..models import Ticket, Embedding
import json
from ..services.embeddings import embed_text, cosine_similarity, MODEL_NAME

router = APIRouter(tags=["search"])

class SearchRequest(BaseModel):
    q: str


@router.post("/search", response_model=List[Ticket])
def search(
    body: SearchRequest,
    session: Session = Depends(get_session),
):
    """
    Simple text search:
    - If q is empty/whitespace → return first 20 latest tickets.
    - Else → filter by q in summary, description, or external_key.
    """
    q = (body.q or "").strip()

    # No query? Just show some recent tickets.
    if not q:
        stmt = select(Ticket).order_by(Ticket.id.desc()).limit(20)
        return session.exec(stmt).all()

    pattern = f"%{q}%"

    stmt = (
        select(Ticket)
        .where(
            Ticket.summary.ilike(pattern)
            | Ticket.description.ilike(pattern)
            | Ticket.external_key.ilike(pattern)
        )
        .order_by(Ticket.id.desc())
        .limit(20)
    )

    results = session.exec(stmt).all()
    print(f"Search '{q}' → {len(results)} results")
    return results
