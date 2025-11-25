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
    try:
        q = (body.q or "").strip()
        if not q:
            return []

        # 1) Embed query into vector
        query_vec = embed_text(q)

        # 2) Load all embeddings for ticket objects
        embeddings = session.exec(
            select(Embedding).where(
                Embedding.object_type == "ticket",
                Embedding.model_name == MODEL_NAME,
            )
        ).all()

        if not embeddings:
            return []  # no embeddings yet

        # 3) Compute similarity scores
        scored: List[tuple[float, int]] = []
        for emb in embeddings:
            vec = json.loads(emb.vector_json)
            score = cosine_similarity(query_vec, vec)
            scored.append((score, emb.object_id))

        # 4) Sort results by score desc
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:20]
        top_ids = [tid for _, tid in top]

        # 5) Fetch the Ticket records
        if not top_ids:
            return []

        tickets = session.exec(
            select(Ticket).where(Ticket.id.in_(top_ids))
        ).all()

        tmap = {t.id: t for t in tickets}
        return [tmap[tid] for _, tid in top if tid in tmap]
    except Exception as e:
        # Log the error for debugging
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Semantic search failed", "detail": str(e)},
        )
