
from pydantic import BaseModel


class CreateSnippetRequest(BaseModel):
    title: str
    content_md: str
    ticket_id: int | None = None
    source: str | None = "user"
    tags: list[str] | None = None


class CreateSnippetResponse(BaseModel):
    id: int
    title: str
    summary: str | None
    content_md: str | None
    echo_score: float


class SnippetFeedbackRequest(BaseModel):
    # Accept either a `snippet_id` (preferred) or a `ticket_id` to allow
    # creating/reusing a snippet based on the ticket context. At least one
    # of these should be provided; router will validate presence.
    snippet_id: int | None = None
    ticket_id: int | None = None
    helped: bool
    notes: str | None = None


class SnippetSearchResult(BaseModel):
    id: int
    title: str
    summary: str | None
    echo_score: float
    success_count: int | None = 0
    failure_count: int | None = 0
    ticket_id: int | None = None


class SnippetFeedbackResponse(BaseModel):
    snippet_id: int
    echo_score: float
