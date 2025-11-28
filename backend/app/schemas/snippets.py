from pydantic import BaseModel
from typing import Optional, List


class CreateSnippetRequest(BaseModel):
    title: str
    content_md: str
    ticket_id: Optional[int] = None
    source: Optional[str] = "user"
    tags: Optional[List[str]] = None


class CreateSnippetResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str]
    content_md: Optional[str]
    echo_score: float


class SnippetFeedbackRequest(BaseModel):
    # Accept either a `snippet_id` (preferred) or a `ticket_id` to allow
    # creating/reusing a snippet based on the ticket context. At least one
    # of these should be provided; router will validate presence.
    snippet_id: Optional[int] = None
    ticket_id: Optional[int] = None
    helped: bool
    notes: Optional[str] = None


class SnippetSearchResult(BaseModel):
    id: int
    title: str
    summary: Optional[str]
    echo_score: float
