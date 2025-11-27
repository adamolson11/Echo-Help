from datetime import datetime

from pydantic import BaseModel


class IntakeRequest(BaseModel):
    text: str


class IntakeSuggestedTicket(BaseModel):
    id: int
    external_key: str
    summary: str
    description: str
    status: str
    priority: str | None = None
    created_at: datetime | None = None
    similarity: float


class IntakeResponse(BaseModel):
    query: str
    suggested_tickets: list[IntakeSuggestedTicket]
    predicted_category: str | None = None
    predicted_subcategory: str | None = None
