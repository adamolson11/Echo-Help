from typing import Any, List, Optional

from pydantic import BaseModel

from backend.app.schemas.snippets import SnippetSearchResult


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
    query: str
    answer: str
    results: List[Any]
    snippets: List[SnippetSearchResult] = []
    kb_backed: bool = False
    kb_confidence: float = 0.0
    # mode: either 'kb_answer' (grounded in KB/tickets) or 'general_answer' (no matches)
    mode: str | None = None
    references: List[AskEchoReference] = []
    reasoning: Optional[AskEchoReasoning] = None
