from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON
from sqlmodel import Column, Field, SQLModel


class Embedding(SQLModel, table=True):
    """Stores a text and its embedding vector for semantic search.

    The `vector` column uses a JSON column to persist lists of floats.
    """

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: int | None = Field(default=None, foreign_key="ticket.id")
    feedback_id: int | None = Field(default=None, foreign_key="ticketfeedback.id")
    text: str
    vector: list[float] = Field(sa_column=Column(JSON))  # type: ignore[reportUnknownMemberType]
    model_name: str = Field(default="all-MiniLM-L6-v2")
    created_at: datetime = Field(default_factory=datetime.utcnow)
