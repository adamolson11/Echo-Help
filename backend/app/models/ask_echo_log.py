from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from backend.app.core.time import utcnow


class AskEchoLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    query: str = Field(index=True)
    top_score: float = 0.0
    kb_confidence: float = 0.0
    mode: str = Field(index=True)
    references_count: int = 0

    # Reasoning / audit fields (Week 3A)
    # JSON string of list of {"id": int, "score": float}
    candidate_snippet_ids_json: str | None = None
    # JSON string of list of snippet ids actually used
    chosen_snippet_ids_json: str | None = None
    # Overall EchoScore for this answer
    echo_score: float | None = None
    # Optional free-text reasoning summary
    reasoning_notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow, index=True)
