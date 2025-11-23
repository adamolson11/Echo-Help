from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Embedding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    object_type: str   # "ticket", "document", "concept"
    object_id: int
    model_name: str
    vector: str  # or bytes, but str for now as placeholder
    created_at: datetime
