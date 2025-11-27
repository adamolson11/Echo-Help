from __future__ import annotations

from datetime import datetime

from ..models.ticket_feedback import TicketFeedbackBase


class TicketFeedbackCreate(TicketFeedbackBase):
    pass


class TicketFeedbackRead(TicketFeedbackBase):
    id: int
    created_at: datetime
