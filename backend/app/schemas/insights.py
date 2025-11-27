from __future__ import annotations

from datetime import datetime

from sqlmodel import SQLModel


class UnhelpfulExample(SQLModel):
    ticket_id: int
    resolution_notes: str | None = None
    created_at: datetime


class TicketFeedbackInsights(SQLModel):
    total_feedback: int
    helped_true: int
    helped_false: int
    helped_null: int
    unhelpful_examples: list[UnhelpfulExample]


# For clustering output
class FeedbackCluster(SQLModel):
    cluster_index: int
    size: int
    example_ticket_ids: list[int]
    example_notes: list[str]
