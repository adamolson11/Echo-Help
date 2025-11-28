from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from backend.app.db import get_session
from backend.app.schemas.snippets import (
    CreateSnippetRequest,
    CreateSnippetResponse,
    SnippetFeedbackRequest,
    SnippetSearchResult,
)
from backend.app.services.snippet_processor import (
    generate_snippet_from_feedback,
    create_snippet_from_feedback_payload,
)
from backend.app.services.confidence_calculator import calculate_echo_score
from backend.app.models.snippets import SolutionSnippet, SnippetFeedback

router = APIRouter(tags=["snippets"])


@router.post("/snippets/create", response_model=CreateSnippetResponse)
def create_snippet(payload: CreateSnippetRequest, session: Session = Depends(get_session)):
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
    snippet = session.get(SolutionSnippet, payload.snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="snippet not found")

    # Persist feedback
    fb = SnippetFeedback(snippet_id=payload.snippet_id, helped=payload.helped, notes=payload.notes)
    session.add(fb)

    # Update counters
    if payload.helped:
        snippet.success_count = (snippet.success_count or 0) + 1
    else:
        snippet.failure_count = (snippet.failure_count or 0) + 1

    # Recalculate echo score
    snippet.echo_score = calculate_echo_score(snippet)

    session.add(snippet)
    session.commit()
    session.refresh(snippet)

    return {"snippet_id": snippet.id, "echo_score": snippet.echo_score}


@router.get("/snippets/search", response_model=List[SnippetSearchResult])
def search_snippets(q: str, limit: int = 10, session: Session = Depends(get_session)):
    qv = (q or "").strip()
    if not qv:
        return []

    stmt = select(SolutionSnippet).where(
        (SolutionSnippet.title.ilike(f"%{qv}%")) | (SolutionSnippet.summary.ilike(f"%{qv}%"))
    ).limit(limit)

    rows = session.exec(stmt).all()
    results = [
        SnippetSearchResult(id=r.id, title=r.title, summary=r.summary, echo_score=r.echo_score) for r in rows
    ]
    return results
