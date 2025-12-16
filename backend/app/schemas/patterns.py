from __future__ import annotations

from typing import Any

from sqlmodel import SQLModel

from .meta import Meta


class FeedbackPatternsStats(SQLModel):
    total_feedback: int
    positive: int
    negative: int
    window_days: int


class FeedbackPatternsSummary(SQLModel):
    meta: Meta = Meta(kind="feedback", version="v1")
    stats: FeedbackPatternsStats
    top_comments: list[Any]
