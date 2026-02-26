from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel

from backend.app.core.time import utcnow


class KBEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    entry_id: str = Field(index=True, unique=True)
    title: str
    body_markdown: str
    tags: list[str] | None = Field(default=None, sa_column=Column(JSON))
    product_area: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)
    source_system: str = Field(default="seed_kb")
    source_url: str | None = Field(default=None, sa_column=Column(Text))
