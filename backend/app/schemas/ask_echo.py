from typing import Any, List, Optional, Literal

from pydantic import BaseModel

from backend.app.schemas.meta import Meta
from backend.app.schemas.snippets import SnippetSearchResult


class AskEchoTicketSummary(BaseModel):
    id: int
    summary: Optional[str] = None
    title: Optional[str] = None


class AskEchoReference(BaseModel):
    ticket_id: int
    confidence: Optional[float] = None


class AskEchoReasoningSnippet(BaseModel):
    id: int
    title: Optional[str] = None
    score: Optional[float] = None


class AskEchoReasoning(BaseModel):
    candidate_snippets: List[AskEchoReasoningSnippet] = []
    chosen_snippet_ids: List[int] = []
    echo_score: Optional[float] = None


class AskEchoRequest(BaseModel):
    q: str
    limit: int = 5


class AskEchoResponse(BaseModel):
    meta: Meta = Meta(kind="ask_echo", version="v1")
    answer_kind: Literal["grounded", "ungrounded"]
    ask_echo_log_id: int
    query: str
    answer: str
    results: List[AskEchoTicketSummary]
    snippets: List[SnippetSearchResult] = []
    kb_backed: bool = False
    kb_confidence: float = 0.0
    # mode: either 'kb_answer' (grounded in KB/tickets) or 'general_answer' (no matches)
    mode: str | None = None
    references: List[AskEchoReference] = []
    reasoning: Optional[AskEchoReasoning] = None
