# ruff: noqa: B008
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import Ticket

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
    q = (body.q or "").strip()

    # No query? Just show some recent tickets.
    if not q:
        stmt = select(Ticket).order_by(Ticket.id.desc())  # type: ignore[reportUnknownMemberType]
        stmt = stmt.limit(20)
        return session.exec(stmt).all()

    pattern = f"%{q}%"

    stmt = (
        select(Ticket)
        .where(
            Ticket.summary.ilike(pattern)  # type: ignore[reportAttributeAccessIssue]
            | Ticket.description.ilike(pattern)  # type: ignore[reportAttributeAccessIssue]
            | Ticket.external_key.ilike(pattern)  # type: ignore[reportAttributeAccessIssue]
        )
        .order_by(Ticket.id.desc())  # type: ignore[reportUnknownMemberType]
        .limit(20)
    )

    results = session.exec(stmt).all()
    print(f"Search '{q}' → {len(results)} results")
    return results
