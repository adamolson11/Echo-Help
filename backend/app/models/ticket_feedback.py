
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class TicketFeedbackBase(SQLModel):
    ticket_id: int
    helped: Optional[bool] = None
    resolution_notes: Optional[str] = None
    # AI stubs for future use
    ai_cluster_id: Optional[str] = None
    ai_summary: Optional[str] = None


class TicketFeedback(TicketFeedbackBase, table=True):
    __tablename__ = "ticketfeedback"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
