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
    """
    Simple dev-safe search: ignore embeddings for now and return
    the first 20 tickets from the database so the UI can show real data.
    """
    print("Search query:", body.q)

    stmt = select(Ticket).limit(20)
    results = session.exec(stmt).all()
    return results
