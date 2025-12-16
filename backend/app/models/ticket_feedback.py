from datetime import datetime

from sqlmodel import Field, SQLModel

from backend.app.core.time import utcnow


class TicketFeedbackBase(SQLModel):
    ticket_id: int
    query_text: str
    rating: int
    helped: bool | None = None
    resolution_notes: str | None = None
    # AI stubs for future use
    ai_cluster_id: str | None = None
    ai_summary: str | None = None


class TicketFeedback(TicketFeedbackBase, table=True):
    # SQLModel/SQLAlchemy uses `__tablename__` declared at runtime; narrow-ignore
    __tablename__ = "ticketfeedback"  # type: ignore[reportAssignmentType]
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
