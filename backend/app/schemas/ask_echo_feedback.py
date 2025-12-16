from __future__ import annotations

from datetime import datetime

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
