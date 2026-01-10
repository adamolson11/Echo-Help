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


class AskEchoRequest(BaseModel):
    q: str
    limit: int = 5


class AskEchoResponse(BaseModel):
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
