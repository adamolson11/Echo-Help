from typing import List, Tuple
from sqlmodel import Session, select
import json

from ..models import Ticket, Embedding
from .embeddings import embed_text, cosine_similarity, MODEL_NAME

def semantic_search_tickets(session: Session, query: str, limit: int = 20) -> List[Tuple[float, Ticket]]:
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

    tickets = session.exec(
        select(Ticket).where(Ticket.id.in_(top_ids))
    ).all()
    tmap = {t.id: t for t in tickets}

    ordered = [
        (score, tmap[tid]) for score, tid in top if tid in tmap
    ]
    return ordered
