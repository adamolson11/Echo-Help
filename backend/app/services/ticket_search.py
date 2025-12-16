from __future__ import annotations

from sqlmodel import Session, select

from backend.app.models.ticket import Ticket


def keyword_search_tickets(session: Session, *, query: str, limit: int = 20) -> list[Ticket]:
    """Shared keyword ticket search used by multiple endpoints.

    Keeps ranking/order consistent across the product.
    """
    q = (query or "").strip()
    if not q:
        stmt = select(Ticket).order_by(Ticket.id.desc())  # type: ignore[reportUnknownMemberType]
        stmt = stmt.limit(limit)
        return list(session.exec(stmt).all())

    pattern = f"%{q}%"
    stmt = (
        select(Ticket)
        .where(
            Ticket.summary.ilike(pattern)  # type: ignore[reportAttributeAccessIssue]
            | Ticket.description.ilike(pattern)  # type: ignore[reportAttributeAccessIssue]
            | Ticket.external_key.ilike(pattern)  # type: ignore[reportAttributeAccessIssue]
        )
        .order_by(Ticket.id.desc())  # type: ignore[reportUnknownMemberType]
        .limit(limit)
    )
    return list(session.exec(stmt).all())
