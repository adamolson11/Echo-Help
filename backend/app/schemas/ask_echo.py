"""Stable Ask Echo response contracts.

`AskEchoResponse` is the frontend-safe public response. Internal/admin-only
inspection routes live in separate schema modules and may expose additional
analytics fields such as weak-answer flags or feedback status.
"""

from typing import Literal

from pydantic import BaseModel

from backend.app.schemas.meta import Meta
from backend.app.schemas.snippets import SnippetSearchResult


class AskEchoTicketSummary(BaseModel):
    id: int
    summary: str | None = None
    title: str | None = None


class AskEchoReference(BaseModel):
    ticket_id: int
    confidence: float | None = None


class AskEchoReasoningSnippet(BaseModel):
    id: int
    title: str | None = None
    score: float | None = None


class AskEchoReasoning(BaseModel):
    candidate_snippets: list[AskEchoReasoningSnippet] = []
    chosen_snippet_ids: list[int] = []
    echo_score: float | None = None


class AskEchoEvidence(BaseModel):
    ticket_id: int
    external_key: str | None = None
    answer_quality_label: Literal["good", "bad", "mixed"] | None = None
    boosts_applied: list[str] = []
    final_score: float | None = None


class AskEchoKBEvidence(BaseModel):
    entry_id: str
    title: str
    source_system: str = "seed_kb"
    source_url: str | None = None
    score: float | None = None


class AskEchoRecommendationSource(BaseModel):
    kind: Literal["ticket", "snippet", "kb", "general"]
    label: str
    ticket_id: int | None = None
    snippet_id: int | None = None
    entry_id: str | None = None
    source_url: str | None = None


class AskEchoRecommendation(BaseModel):
    id: str
    title: str
    summary: str
    rationale: str
    confidence: float | None = None
    source: AskEchoRecommendationSource
    steps: list[str] = []


class AskEchoFlywheelState(BaseModel):
    current_stage: Literal[
        "recommendations_ready",
        "action_selected",
        "outcome_recorded",
        "learning_captured",
    ] = "recommendations_ready"
    recommended_action_count: int = 3
    selected_recommendation_id: str | None = None
    outcome_recorded: bool = False
    reusable_learning_saved: bool = False


class AskEchoFlywheel(BaseModel):
    issue: str
    state: AskEchoFlywheelState = AskEchoFlywheelState()
    recommendations: list[AskEchoRecommendation] = []
    outcome_options: list[Literal["resolved", "partially_resolved", "not_resolved", "needs_escalation"]] = [
        "resolved",
        "partially_resolved",
        "not_resolved",
        "needs_escalation",
    ]
    reusable_learning_prompt: str = (
        "Capture what Echo should remember next time: the winning step, when to use it, and any escalation signal."
    )


class AskEchoRequest(BaseModel):
    q: str
    limit: int = 5


class AskEchoResponse(BaseModel):
    """Public Ask Echo response safe for UI consumption."""

    meta: Meta = Meta(kind="ask_echo", version="v2")
    answer_kind: Literal["grounded", "ungrounded"]
    ask_echo_log_id: int
    query: str
    answer: str
    # Explicit suggestion fields (avoid generic names like `results`).
    suggested_tickets: list[AskEchoTicketSummary]
    suggested_snippets: list[SnippetSearchResult] = []
    kb_backed: bool = False
    kb_confidence: float = 0.0
    # mode: either 'kb_answer' (grounded in KB/tickets) or 'general_answer' (no matches)
    mode: str | None = None
    references: list[AskEchoReference] = []
    reasoning: AskEchoReasoning | None = None
    evidence: list[AskEchoEvidence] = []
    kb_evidence: list[AskEchoKBEvidence] = []
    flywheel: AskEchoFlywheel
