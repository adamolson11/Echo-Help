from sqlmodel import Session, select
import logging

from ..models import Embedding, Ticket
from .embeddings import MODEL_NAME, cosine_similarity, embed_text


def semantic_search_tickets(
    session: Session, query: str, limit: int = 20
) -> list[tuple[float, Ticket]]:
    q = (query or "").strip()
    if not q:
        return []

    query_vec = embed_text(q)

    # Select embeddings that are associated with tickets and match the model
    embeddings = session.exec(
        select(Embedding).where(
            Embedding.model_name == MODEL_NAME,
            Embedding.ticket_id.is_not(None),  # type: ignore[reportAttributeAccessIssue]
        )
    )
    embeddings = list(embeddings.all())

    if not embeddings:
        return []

    scored = []
    logger = logging.getLogger(__name__)

    for emb in embeddings:
        # emb.vector is stored as JSON-backed list[float]
        vec = emb.vector
        # Skip invalid vectors (non-list) and dimensionality mismatches.
        if not isinstance(vec, (list, tuple)):
            logger.warning("Skipping embedding id=%s: vector is not a list/tuple", getattr(emb, 'id', 'unknown'))
            continue
        if len(vec) != len(query_vec):
            # skip vectors that don't align with the query embedding dim
            logger.warning(
                "Skipping embedding id=%s: dim mismatch %s vs %s",
                getattr(emb, 'id', 'unknown'),
                len(vec),
                len(query_vec),
            )
            continue
        score = cosine_similarity(query_vec, vec)
        if emb.ticket_id is None:
            continue
        scored.append((score, emb.ticket_id))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]
    top_ids = [tid for _, tid in top]

    # SQLModel/SQLAlchemy expression `.in_` isn't fully visible to the type
    # checker here; narrow-ignore the attribute-access/argument typing.
    tickets = session.exec(select(Ticket).where(Ticket.id.in_(top_ids)))  # type: ignore[reportUnknownMemberType]
    tickets = tickets.all()
    tmap = {t.id: t for t in tickets}

    ordered = [(score, tmap[tid]) for score, tid in top if tid in tmap]
    return ordered
