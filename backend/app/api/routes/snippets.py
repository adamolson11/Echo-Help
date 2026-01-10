# ruff: noqa: B008

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from backend.app.db import get_session
from backend.app.schemas.snippets import (
    CreateSnippetRequest,
    CreateSnippetResponse,
    SnippetFeedbackRequest,
    SnippetFeedbackResponse,
    SnippetSearchResult,
)
from backend.app.services.snippet_processor import generate_snippet_from_feedback
from backend.app.services.snippet_repository import (
    increment_feedback_and_recalculate_score,
)
from backend.app.services.snippet_repository import search_snippets as repo_search_snippets

router = APIRouter(tags=["snippets"])


@router.post("/snippets/create", response_model=CreateSnippetResponse)
def create_snippet(
    payload: CreateSnippetRequest, session: Session = Depends(get_session)
):
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

    assert snippet.id is not None
    return CreateSnippetResponse(
        id=snippet.id,
        title=snippet.title,
        summary=snippet.summary,
        content_md=snippet.content_md,
        echo_score=snippet.echo_score,
    )


@router.post("/snippets/feedback", response_model=SnippetFeedbackResponse)
def submit_snippet_feedback(
    payload: SnippetFeedbackRequest, session: Session = Depends(get_session)
):
    # Validate presence of an identifier
    if not payload.snippet_id and not payload.ticket_id:
        raise HTTPException(status_code=400, detail="snippet_id or ticket_id required")

    # If snippet_id provided, use it. Otherwise try to find or create a snippet for ticket_id
    snippet_id = payload.snippet_id
    if not snippet_id and payload.ticket_id:
        # try to ensure a snippet exists for that ticket
        try:
            from backend.app.services.snippet_processor import ensure_snippet_for_feedback

            snippet = ensure_snippet_for_feedback(
                session=session,
                ticket_id=payload.ticket_id,
                feedback_notes=payload.notes or "",
            )
            snippet_id = snippet.id
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="failed to ensure snippet for ticket"
            ) from e

    if snippet_id is None:
        raise HTTPException(status_code=500, detail="missing snippet_id")

    # Increment counters and recalc atomically
    try:
        updated = increment_feedback_and_recalculate_score(
            session, snippet_id, payload.helped, payload.notes
        )
    except ValueError as e:
        # bubble up not found as 404
        if str(e).lower().startswith("snippet not found"):
            raise HTTPException(status_code=404, detail="Snippet not found") from e
        raise HTTPException(status_code=500, detail="feedback update failed") from e

    assert updated.id is not None
    return {"snippet_id": updated.id, "echo_score": updated.echo_score}


@router.get("/snippets/search", response_model=list[SnippetSearchResult])
def search_snippets(
    q: str = Query("", description="Search query"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    qv = (q or "").strip()
    if not qv:
        return []

    rows = repo_search_snippets(session, qv, limit=limit, offset=offset)
    results = []
    for r in rows:
        if r.id is None:
            continue
        results.append(
            SnippetSearchResult(
                id=r.id,
                title=r.title,
                summary=r.summary,
                echo_score=r.echo_score,
                success_count=getattr(r, "success_count", 0),
                failure_count=getattr(r, "failure_count", 0),
                ticket_id=getattr(r, "ticket_id", None),
            )
        )
    return results
