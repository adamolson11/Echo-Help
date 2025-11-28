from __future__ import annotations

from pydantic import BaseModel


class SemanticSearchRequest(BaseModel):
    q: str
    limit: int = 10


class SemanticSearchResult(BaseModel):
    ticket_id: int
    score: float
    summary: str
    description: str | None = None
