from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import Session, select

from backend.app.models.snippets import SnippetFeedback, SolutionSnippet
from backend.app.models.ticket import Ticket


def generate_snippet_from_feedback(
    title: str,
    content_md: str,
    session: Session,
    ticket_id: int | None = None,
    source: str = "user",
    tags: Sequence[str] | None = None,
) -> SolutionSnippet:
    """Create and persist a SolutionSnippet record.

    This is intentionally minimal for Phase 1: it stores the Markdown
    content, optional tags, and initial echo_score/default counters.
    """
    snippet = SolutionSnippet(
        ticket_id=ticket_id,
        title=title,
        summary=(content_md or "")[:200],
        content_md=content_md,
        source=source,
        echo_score=0.0,
        success_count=0,
        failure_count=0,
        tags=list(tags) if tags else None,
    )

    session.add(snippet)
    session.commit()
    session.refresh(snippet)
    return snippet


def create_snippet_from_feedback_payload(
    feedback_notes: str,
    helped: bool,
    session: Session,
    ticket_id: int | None = None,
) -> SolutionSnippet:
    """Convenience wrapper used when feedback arrives from the UI/API.

    For Phase 1 we generate a simple snippet and record a SnippetFeedback
    row. Summarization is a light-weight fallback; a future step can call
    an LLM summarizer to produce richer `content_md`.
    """
    # Produce a lightweight title and content
    title = None
    if ticket_id:
        t = session.exec(select(Ticket).where(Ticket.id == ticket_id)).one_or_none()
        if t:
            title = f"Solution for {t.summary or 'ticket'}"

    if not title:
        # Fallback title from the first line of notes
        first_line = (feedback_notes or "").splitlines()[0][:80]
        title = f"Snippet: {first_line or 'user feedback'}"

    content_md = f"### Reported fix\n\n{feedback_notes}\n"

    snippet = generate_snippet_from_feedback(
        title=title, content_md=content_md, session=session, ticket_id=ticket_id
    )

    # Store the feedback row
    assert snippet.id is not None
    fb = SnippetFeedback(
        snippet_id=snippet.id, helped=bool(helped), notes=feedback_notes
    )
    session.add(fb)
    session.commit()

    return snippet


def summarize_resolution_with_ai(query: str, notes: str) -> str:
    """Placeholder summarizer for Phase 1.

    In later phases this can call an LLM to produce a concise Markdown
    snippet. For now, return a simple structured summary.
    """
    # Minimal heuristic: include query and a short excerpt of notes
    excerpt = (notes or "").strip()
    if len(excerpt) > 800:
        excerpt = excerpt[:800] + "..."
    return f"**Summary for**: {query}\n\n{excerpt}\n"


def ensure_snippet_for_feedback(
    session: Session, ticket_id: int, feedback_notes: str
) -> SolutionSnippet:
    """Find or create a snippet associated with `ticket_id`.

    If a snippet already exists for the ticket, return it. Otherwise create
    a minimal snippet using the ticket summary and feedback notes.
    """
    if not ticket_id:
        raise ValueError("ticket_id required")

    # Try to find existing snippet for ticket
    existing = session.exec(
        select(SolutionSnippet).where(SolutionSnippet.ticket_id == ticket_id)
    ).first()
    if existing:
        return existing

    # Build a snippet from ticket and notes
    t = session.exec(select(Ticket).where(Ticket.id == ticket_id)).one_or_none()
    title = None
    if t:
        title = f"Solution for {t.summary or ('ticket-'+str(ticket_id))}"

    if not title:
        title = f"Snippet from feedback for ticket {ticket_id}"

    content_md = f"### Auto-generated snippet from feedback\n\n{feedback_notes or ''}\n"

    snippet = generate_snippet_from_feedback(
        title=title, content_md=content_md, session=session, ticket_id=ticket_id
    )
    return snippet
