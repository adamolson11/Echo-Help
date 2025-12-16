# ruff: noqa: B008
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from ..db import get_session
from ..models import Ticket
from ..services.ticket_search import keyword_search_tickets

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    q: str


@router.post("/search", response_model=list[Ticket])
def search(
    body: SearchRequest,
    session: Session = Depends(get_session),
):
    """
    Simple text search:
    - If q is empty/whitespace → return first 20 latest tickets.
    - Else → filter by q in summary, description, or external_key.
    """
    tickets = keyword_search_tickets(session, query=body.q, limit=20)
    return tickets
