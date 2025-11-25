from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class IntakeRequest(BaseModel):
    text: str

class IntakeSuggestedTicket(BaseModel):
    id: int
    external_key: str
    summary: str
    description: str
    status: str
    priority: Optional[str] = None
    created_at: Optional[datetime] = None
    similarity: float

class IntakeResponse(BaseModel):
    query: str
    suggested_tickets: List[IntakeSuggestedTicket]
    predicted_category: Optional[str] = None
    predicted_subcategory: Optional[str] = None
