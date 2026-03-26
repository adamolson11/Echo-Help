from sqlalchemy import or_
from sqlmodel import Session, col, select

from ..models.snippets import SnippetFeedback, SolutionSnippet
from .ranking_policy import rank_snippets
from .support_query_expansion import search_query_variants


def get_snippet_by_id(session: Session, snippet_id: int) -> SolutionSnippet | None:
    return session.get(SolutionSnippet, snippet_id)


def search_snippets(
    session: Session, query: str, limit: int = 10, offset: int = 0
) -> list[SolutionSnippet]:
    variants = search_query_variants(query) or [query]
    clauses = []
    for variant in variants:
        pattern = f"%{variant}%"
        clauses.extend(
            [
                col(SolutionSnippet.title).ilike(pattern),
                col(SolutionSnippet.summary).ilike(pattern),
            ]
        )

    stmt = (
        select(SolutionSnippet)
        .where(or_(*clauses))
        # Keep paging deterministic; ranking happens within the returned page.
        .order_by(SolutionSnippet.updated_at.desc(), SolutionSnippet.id.desc())  # type: ignore[reportUnknownMemberType]
        .offset(offset)
        .limit(max(limit * 8, limit))
    )
    rows = list(session.exec(stmt).all())
    ranked = rank_snippets(candidates=rows, query=query)
    return [rs.snippet for rs in ranked[:limit]]


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
