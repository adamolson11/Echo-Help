from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlmodel import SQLModel

class UnhelpfulExample(SQLModel):
    ticket_id: int
    resolution_notes: Optional[str] = None
    created_at: datetime


class TicketFeedbackInsights(SQLModel):
    total_feedback: int
    helped_true: int
    helped_false: int
    helped_null: int
    unhelpful_examples: List[UnhelpfulExample]


# For clustering output
class FeedbackCluster(SQLModel):
    cluster_index: int
    size: int
    example_ticket_ids: List[int]
    example_notes: List[str]
