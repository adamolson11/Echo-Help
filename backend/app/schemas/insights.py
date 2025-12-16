from __future__ import annotations

from datetime import datetime

from sqlmodel import SQLModel

from .meta import Meta


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
    items: list["AskEchoLogSummary"]


class AskEchoLogSummary(SQLModel):
    id: int
    query_text: str
    ticket_id: int | None = None
    echo_score: float | None = None
    created_at: str | None = None


class AskEchoFeedbackResponse(SQLModel):
    meta: Meta = Meta(kind="ask_echo_feedback", version="v1")


class AskEchoFeedbackRow(SQLModel):
    id: int
    ask_echo_log_id: int
    helped: bool
    notes: str | None = None
    query_text: str | None = None
    created_at: str | None = None


class AskEchoFeedbackResponse(SQLModel):
    meta: Meta = Meta(kind="ask_echo_feedback", version="v1")
    items: list[AskEchoFeedbackRow]


class ReasoningSnippetCandidate(SQLModel):
    id: int
    title: str | None = None
    score: float | None = None


class AskEchoLogReasoning(SQLModel):
    candidate_snippets: list[ReasoningSnippetCandidate] = []
    chosen_snippet_ids: list[int] = []


class AskEchoLogDetail(SQLModel):
    id: int
    query_text: str
    answer_text: str
    ticket_id: int | None = None
    echo_score: float | None = None
    created_at: str | None = None
    reasoning: AskEchoLogReasoning | None = None
    reasoning_notes: str | None = None


class AskEchoLogDetailResponse(SQLModel):
    meta: Meta = Meta(kind="ask_echo_log_detail", version="v1")
    item: AskEchoLogDetail


# Pattern Radar schemas
class SnippetPatternSummary(SQLModel):
    snippet_id: int
    problem_summary: str
    total_uses: int
    successes: int
    failures: int


class PatternRadarStats(SQLModel):
    total_snippets: int
    total_successes: int
    total_failures: int


class PatternRadarResponse(SQLModel):
    meta: Meta = Meta(kind="snippet", version="v1")
    stats: PatternRadarStats
    top_frequent_snippets: list[SnippetPatternSummary]
    top_risky_snippets: list[SnippetPatternSummary]


class PatternKeyword(SQLModel):
    keyword: str
    count: int


class PatternTitle(SQLModel):
    title: str
    count: int


class TicketPatternRadarStats(SQLModel):
    total_tickets: int
    window_days: int
    first_ticket_at: str | None = None
    last_ticket_at: str | None = None


class TicketPatternRadarResponse(SQLModel):
    meta: Meta = Meta(kind="ticket", version="v1")
    top_keywords: list[PatternKeyword]
    frequent_titles: list[PatternTitle]
    semantic_clusters: list[dict]
    stats: TicketPatternRadarStats
