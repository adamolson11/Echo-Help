from __future__ import annotations

# ruff: noqa: B008
import numpy as np
from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlmodel import Session, col, select

from ..db import get_session
from ..models.embedding import Embedding
from ..models.ticket import Ticket
from ..schemas.semantic_search import SemanticSearchRequest, SemanticSearchResult
from ..services.embeddings import embed_text

router = APIRouter(tags=["semantic-search"])


@router.post("/semantic-search", response_model=list[SemanticSearchResult])
def semantic_search(
    body: SemanticSearchRequest, session: Session = Depends(get_session)
) -> list[SemanticSearchResult]:
    q = (body.q or "").strip()
    if not q:
        return []

    query_vec = embed_text(q)
    query_arr = np.asarray(query_vec, dtype=float)

    # Build a statement joining embeddings to their tickets and apply filters
    stmt = select(Embedding, Ticket).join(Ticket, col(Ticket.id) == col(Embedding.ticket_id))

    # Apply status filter if provided
    status = body.status
    if status and status != "all":
        s = status.lower()
        if s == "open":
            stmt = stmt.where(col(Ticket.status).ilike("%open%"))
        elif s == "closed":
            stmt = stmt.where(
                or_(
                    col(Ticket.status).ilike("%closed%"),
                    col(Ticket.status).ilike("%resolved%"),
                )
            )
        elif s == "other":
            stmt = stmt.where(~col(Ticket.status).ilike("%open%"))
            stmt = stmt.where(~col(Ticket.status).ilike("%closed%"))
            stmt = stmt.where(~col(Ticket.status).ilike("%resolved%"))
        else:
            # attempt direct match
            stmt = stmt.where(col(Ticket.status).ilike(f"%{status}%"))

    # Apply priority filter if provided
    priority = body.priority
    if priority and priority != "all":
        p = priority.lower()
        stmt = stmt.where(col(Ticket.priority).ilike(f"%{p}%"))

    rows: list[tuple[Embedding, Ticket]] = list(session.exec(stmt).all())
    if not rows:
        return []

    # Ensure all embedding vectors have the same dimensionality as the query.
    # Some tests insert small dummy vectors; skip those that don't match to avoid
    # matmul dimension errors.
    expected_dim = query_arr.shape[0]
    # rows contain (Embedding, Ticket) tuples
    valid_pairs: list[tuple[Embedding, Ticket]] = []
    for emb_obj, ticket_obj in rows:

        if not isinstance(emb_obj.vector, (list, tuple)):
            continue
        if len(emb_obj.vector) != expected_dim:
            continue
        valid_pairs.append((emb_obj, ticket_obj))

    if not valid_pairs:
        return []

    matrix = np.asarray([e.vector for e, _ in valid_pairs], dtype=float)  # type: ignore[reportUnknownArgumentType]

    # Compute cosine similarity
    query_norm = np.linalg.norm(query_arr)
    mat_norms = np.linalg.norm(matrix, axis=1)
    denom = mat_norms * query_norm
    # avoid div-by-zero
    denom[denom == 0] = 1e-8

    scores = (matrix @ query_arr) / denom

    # pick top N
    limit = max(1, body.limit)
    idxs = np.argsort(-scores)[:limit]

    results: list[SemanticSearchResult] = []
    for i in idxs:
        emb_obj, ticket_obj = valid_pairs[int(i)]
        if ticket_obj is None:
            continue
        if ticket_obj.id is None:
            continue
        results.append(
            SemanticSearchResult(
                ticket_id=ticket_obj.id,
                score=float(scores[int(i)]),
                summary=ticket_obj.summary or "",
                description=ticket_obj.description,
            )
        )

    return results
