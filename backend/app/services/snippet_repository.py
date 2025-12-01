from typing import List, Optional

from sqlmodel import Session, select

from backend.app.models.snippets import SnippetFeedback, SolutionSnippet


def get_snippet_by_id(session: Session, snippet_id: int) -> Optional[SolutionSnippet]:
    return session.get(SolutionSnippet, snippet_id)


def search_snippets(
    session: Session, query: str, limit: int = 10, offset: int = 0
) -> List[SolutionSnippet]:
    q = f"%{query}%"
    stmt = (
        select(SolutionSnippet)
        .where((SolutionSnippet.title.ilike(q)) | (SolutionSnippet.summary.ilike(q)))
        .offset(offset)
        .limit(limit)
    )
    rows = session.exec(stmt).all()
    return rows


def increment_feedback_and_recalculate_score(
    session: Session, snippet_id: int, helped: bool, notes: str | None = None
) -> SolutionSnippet:
    snippet = session.get(SolutionSnippet, snippet_id)
    if not snippet:
        raise ValueError("Snippet not found")

    # persist feedback
    fb = SnippetFeedback(snippet_id=snippet_id, helped=helped, notes=notes)
    session.add(fb)

    # update counters
    if helped:
        snippet.success_count = (snippet.success_count or 0) + 1
    else:
        snippet.failure_count = (snippet.failure_count or 0) + 1

    # recalc score using existing calculator import deferred by caller
    from backend.app.services.confidence_calculator import calculate_echo_score

    snippet.echo_score = calculate_echo_score(snippet)

    session.add(snippet)
    session.commit()
    session.refresh(snippet)
    return snippet
