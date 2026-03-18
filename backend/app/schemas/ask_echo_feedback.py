"""Ask Echo feedback contracts.

UI-safe stable fields:
- Public feedback submission/read models below.
- Internal inspection route models expose analytics and weak-answer flags for
  admin/debug surfaces only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from backend.app.schemas.meta import Meta


class AskEchoFeedbackCreate(BaseModel):
    ask_echo_log_id: int
    helped: bool
    notes: str | None = None


class AskEchoFeedbackRead(BaseModel):
    id: int
    ask_echo_log_id: int
    helped: bool
    notes: str | None
    created_at: datetime


class AskEchoFeedbackSummaryResponse(BaseModel):
    meta: Meta = Meta(kind="ask_echo_feedback_summary", version="v1")
    window_days: int
    total_feedback: int
    helped_true: int
    helped_false: int


class AskEchoFeedbackInspectionRecord(BaseModel):
    ask_echo_log_id: int
    question: str
    answer: str
    confidence: float
    source_count: int
    sources: list[str]
    reasoning: str
    rating: int
    feedback_status: Literal["pending", "helped", "not_helped"]
    feedback_notes: str | None = None
    created_at: str | None = None
    feedback_at: str | None = None
    low_confidence: bool
    no_sources: bool
    fallback_only: bool


class AskEchoFeedbackInspectionResponse(BaseModel):
    meta: Meta = Meta(kind="ask_echo_feedback_records", version="v1")
    items: list[AskEchoFeedbackInspectionRecord]
