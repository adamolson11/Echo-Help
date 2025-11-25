from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field

class TicketFeedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int
    query_text: str
    rating: int  # 1–5
    created_at: datetime = Field(default_factory=datetime.utcnow)
