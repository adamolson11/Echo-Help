from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from backend.app.core.time import utcnow


class OrchestrationAgentPass(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cycle_id: int = Field(foreign_key="orchestrationcycle.id", index=True)
    agent_name: str = Field(index=True)
    role: str
    pass_index: int = 1
    status: str = Field(default="completed", index=True)
    response_json: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utcnow, index=True)
