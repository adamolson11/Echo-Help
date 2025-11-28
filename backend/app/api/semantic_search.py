from __future__ import annotations

# ruff: noqa: B008
import numpy as np
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

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

    # Load embeddings that are associated with tickets
    emb_rows = list(
        session.exec(select(Embedding).where(Embedding.ticket_id.is_not(None)))  # type: ignore[reportAttributeAccessIssue]
    )
    if not emb_rows:
        return []

    # Ensure all embedding vectors have the same dimensionality as the query.
    # Some tests insert small dummy vectors; skip those that don't match to avoid
    # matmul dimension errors.
    expected_dim = query_arr.shape[0]
    filtered_rows = [e for e in emb_rows if isinstance(e.vector, (list, tuple)) and len(e.vector) == expected_dim]
    if not filtered_rows:
        return []

    matrix = np.asarray([e.vector for e in filtered_rows], dtype=float)  # type: ignore[reportUnknownArgumentType]

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
        emb = filtered_rows[int(i)]
        if emb.ticket_id is None:
            continue
        ticket = session.get(Ticket, emb.ticket_id)
        if ticket is None:
            continue
        results.append(
            SemanticSearchResult(
                ticket_id=ticket.id,  # type: ignore[arg-type]
                score=float(scores[int(i)]),
                summary=ticket.summary or "",
                description=ticket.description,
            )
        )

    return results
