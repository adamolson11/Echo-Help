from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List

from backend.app.db import get_session
from backend.app.schemas.snippets import (
    CreateSnippetRequest,
    CreateSnippetResponse,
    SnippetFeedbackRequest,
    SnippetSearchResult,
)
from backend.app.services.snippet_processor import generate_snippet_from_feedback
from backend.app.services.confidence_calculator import calculate_echo_score
from backend.app.models.snippets import SnippetFeedback
from backend.app.services.snippet_repository import (
    get_snippet_by_id,
    search_snippets as repo_search_snippets,
    increment_feedback_and_recalculate_score,
)


router = APIRouter(tags=["snippets"])


@router.post("/snippets/create", response_model=CreateSnippetResponse)
def create_snippet(payload: CreateSnippetRequest, session: Session = Depends(get_session)):
    # basic validation is enforced by Pydantic schema; enforce non-empty title/content
    if not payload.title or not payload.content_md:
        raise HTTPException(status_code=400, detail="title and content_md are required")

    snippet = generate_snippet_from_feedback(
        title=payload.title,
        content_md=payload.content_md,
        session=session,
        ticket_id=payload.ticket_id,
        source=payload.source or "user",
        tags=payload.tags,
    )
    return CreateSnippetResponse(
        id=snippet.id,
        title=snippet.title,
        summary=snippet.summary,
        content_md=snippet.content_md,
        echo_score=snippet.echo_score,
    )


@router.post("/snippets/feedback")
def submit_snippet_feedback(payload: SnippetFeedbackRequest, session: Session = Depends(get_session)):
    # Validate snippet exists
    snippet = get_snippet_by_id(session, payload.snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="snippet not found")

    # Increment counters and recalc atomically
    updated = increment_feedback_and_recalculate_score(session, payload.snippet_id, payload.helped, payload.notes)

    return {"snippet_id": updated.id, "echo_score": updated.echo_score}


@router.get("/snippets/search", response_model=List[SnippetSearchResult])
def search_snippets(q: str = Query("", description="Search query"), limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0), session: Session = Depends(get_session)):
    qv = (q or "").strip()
    if not qv:
        return []

    rows = repo_search_snippets(session, qv, limit=limit, offset=offset)
    results = [SnippetSearchResult(id=r.id, title=r.title, summary=r.summary, echo_score=r.echo_score) for r in rows]
    return results
