from __future__ import annotations

from sqlalchemy import or_
from sqlmodel import Session, select

from ..models.ticket import Ticket
from .ranking_policy import rank_tickets
from .support_query_expansion import search_query_variants


def keyword_search_tickets(session: Session, *, query: str, limit: int = 20) -> list[Ticket]:
    """Shared keyword ticket search used by multiple endpoints.

    Keeps ranking/order consistent across the product.
    """
    q = (query or "").strip()
    if not q:
        stmt = select(Ticket).order_by(Ticket.id.desc())  # type: ignore[reportUnknownMemberType]
        stmt = stmt.limit(limit)
        return list(session.exec(stmt).all())

    variants = search_query_variants(q) or [q]
    clauses = []
    for variant in variants:
        pattern = f"%{variant}%"
        clauses.extend(
            [
                Ticket.summary.ilike(pattern),  # type: ignore[reportAttributeAccessIssue]
                Ticket.description.ilike(pattern),  # type: ignore[reportAttributeAccessIssue]
                Ticket.external_key.ilike(pattern),  # type: ignore[reportAttributeAccessIssue]
            ]
        )

    # Pull a slightly larger candidate set, then apply the central ranking policy.
    stmt = (
        select(Ticket)
        .where(or_(*clauses))
        # Ensure the candidate *set* is deterministic before policy ranking.
        .order_by(Ticket.updated_at.desc(), Ticket.id.desc())  # type: ignore[reportUnknownMemberType]
        .limit(max(limit * 12, limit))
    )
    candidates = list(session.exec(stmt).all())
    ranked = rank_tickets(session, candidates=candidates, query=q)
    return [rt.ticket for rt in ranked[:limit]]
