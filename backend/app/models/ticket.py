from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

class Ticket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_key: str
    source: str
    project_key: str
    summary: str
    description: str
    status: str
    priority: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

class Subcategory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="category.id")
    name: str

class TicketFeedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="ticket.id")
    query_text: str
    rating: int  # 1–5 scale for “did this help?”
    created_at: datetime
