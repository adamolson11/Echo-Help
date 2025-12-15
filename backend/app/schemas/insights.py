from __future__ import annotations

from datetime import datetime

from sqlmodel import SQLModel


class Meta(SQLModel):
    kind: str
    version: str


class UnhelpfulExample(SQLModel):
    ticket_id: int
    resolution_notes: str | None = None
    created_at: datetime


class TicketFeedbackInsights(SQLModel):
    meta: Meta = Meta(kind="ticket_feedback_insights", version="v1")
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


class FeedbackClustersResponse(SQLModel):
    meta: Meta = Meta(kind="ticket_feedback_clusters", version="v1")
    clusters: list[FeedbackCluster]


class AskEchoLogsResponse(SQLModel):
    meta: Meta = Meta(kind="ask_echo_logs", version="v1")
    items: list[dict]


class AskEchoFeedbackResponse(SQLModel):
    meta: Meta = Meta(kind="ask_echo_feedback", version="v1")
    items: list[dict]


# Pattern Radar schemas
class SnippetPatternSummary(SQLModel):
    id: int
    problem_summary: str
    echo_score: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    failure_rate: float = 0.0
    source_ticket_id: int | None = None


class PatternRadarStats(SQLModel):
    total_snippets: int
    total_successes: int
    total_failures: int


class PatternRadarResponse(SQLModel):
    stats: PatternRadarStats
    top_frequent_snippets: list[SnippetPatternSummary]
    top_risky_snippets: list[SnippetPatternSummary]
