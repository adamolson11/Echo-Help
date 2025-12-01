from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AskEchoLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    query: str = Field(index=True)
    top_score: float = 0.0
    kb_confidence: float = 0.0
    mode: str = Field(index=True)
    references_count: int = 0

    # Reasoning / audit fields (Week 3A)
    # JSON string of list of {"id": int, "score": float}
    candidate_snippet_ids_json: Optional[str] = None
    # JSON string of list of snippet ids actually used
    chosen_snippet_ids_json: Optional[str] = None
    # Overall EchoScore for this answer
    echo_score: Optional[float] = None
    # Optional free-text reasoning summary
    reasoning_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
