from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from backend.app.core.time import utcnow


class AskEchoFeedback(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ask_echo_log_id: int = Field(index=True)
    helped: bool
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow, index=True)
