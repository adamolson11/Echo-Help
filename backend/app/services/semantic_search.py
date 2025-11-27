import json

from sqlmodel import Session, select

from ..models import Embedding, Ticket
from .embeddings import MODEL_NAME, cosine_similarity, embed_text


def semantic_search_tickets(
    session: Session, query: str, limit: int = 20
) -> list[tuple[float, Ticket]]:
    q = (query or "").strip()
    if not q:
        return []

    query_vec = embed_text(q)

    embeddings = session.exec(
        select(Embedding).where(
            Embedding.object_type == "ticket",
            Embedding.model_name == MODEL_NAME,
        )
    ).all()

    if not embeddings:
        return []

    scored = []
    for emb in embeddings:
        vec = json.loads(emb.vector_json)
        score = cosine_similarity(query_vec, vec)
        scored.append((score, emb.object_id))

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
