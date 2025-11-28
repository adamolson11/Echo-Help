from pydantic import BaseModel
from typing import Any, List

from backend.app.schemas.snippets import SnippetSearchResult


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
    mode: None | str = None
