from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class AskEchoLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    query: str = Field(index=True)
    top_score: float = 0.0
    kb_confidence: float = 0.0
    mode: str = Field(index=True)
    references_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
