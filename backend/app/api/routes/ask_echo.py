from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.schemas.ask_echo import AskEchoRequest, AskEchoResponse
from backend.app.services.semantic_search import semantic_search_tickets
from backend.app.db import get_session
from backend.app.models.ticket import Ticket
from backend.app.services.snippet_repository import search_snippets as repo_search_snippets
import logging
from typing import Tuple


def _truncate(text: str | None, length: int = 240) -> str:
    if not text:
        return ""
    t = str(text).strip()
    if len(t) <= length:
        return t
    return t[:length].rsplit(" ", 1)[0] + "..."


def build_ask_echo_answer(query: str, snippets: list, tickets: list) -> Tuple[str, bool, float, str]:
    """Compose a human-readable answer string and KB metadata from snippets and tickets.

    Returns: (answer, kb_backed, kb_confidence, mode)
    mode is one of: 'KB_ONLY', 'KB_AND_TICKETS', 'TICKETS_ONLY', 'NO_KB'
    """
    if snippets:
        # Use top 3 snippets
        top = sorted(snippets, key=lambda s: (s.echo_score or 0.0, s.success_count or 0), reverse=True)
        top_snips = top[:3]
        bullets = []
        for s in top_snips:
            title = s.title or s.summary or f"Snippet {s.id}"
            resolution = _truncate(s.content_md or s.summary or "")
            bullets.append(f"- {title}: {resolution}")

        answer = "Here’s what has worked most often in your environment:\n" + "\n".join(bullets)
        kb_confidence = float(getattr(top_snips[0], "echo_score", 0.0) or 0.0)
        kb_backed = True
        if tickets:
            mode = "KB_AND_TICKETS"
        else:
            mode = "KB_ONLY"
        return answer, kb_backed, kb_confidence, mode

    # No snippets
    if tickets:
        parts = []
        for t in tickets[:3]:
            title = getattr(t, "summary", None) or getattr(t, "title", None) or f"ticket-{t.id}"
            parts.append(f"- Ticket #{t.id}: {_truncate(title, 120)}")
        answer = (
            "I didn’t find a stored solution snippet, but these prior tickets may help:\n"
            + "\n".join(parts)
        )
        return answer, False, 0.0, "TICKETS_ONLY"

    # No KB and no tickets
    answer = (
        "I couldn’t find any matching tickets or saved solutions in your knowledge base for this query.\n\n"
        "This means the answer is not yet in your EchoHelp database. You can still try general troubleshooting, "
        "and once you resolve it, log the fix so EchoHelp remembers it next time."
    )
    return answer, False, 0.0, "NO_KB"

router = APIRouter(tags=["ask-echo"])  # will be included with prefix="/api" in main


@router.post("/ask-echo", response_model=AskEchoResponse)
def ask_echo(req: AskEchoRequest, session: Session = Depends(get_session)):
    if not req.q or not req.q.strip():
        raise HTTPException(status_code=400, detail="query required")

    # Run semantic search to gather top related tickets (score, Ticket)
    scored = semantic_search_tickets(session=session, query=req.q, limit=req.limit)

    tickets = [t for _, t in scored]

    # Build a concise answer: count + top title + short bullets
    if tickets:
        top = tickets[0]
        top_title = getattr(top, "summary", None) or getattr(top, "title", None) or "a related ticket"
        parts = []
        for t in tickets:
            title = getattr(t, "summary", "") or getattr(t, "title", "")
            desc = (getattr(t, "description", "") or "").strip()
            snippet = desc[:200].split("\n")[0]
            parts.append(f"- {title}: {snippet}")

        answer = (
            f"I found {len(tickets)} relevant prior ticket(s). The top match appears to be '{top_title}'.\n"
            "\n" + "\n".join(parts)
        )
    else:
        answer = "I couldn't find relevant tickets."

    # Safety note for experimental AI output
    answer = answer + "\n\nNote: This is experimental AI output — verify details before applying fixes." 

    # Find matching snippets in the KB and sort by echo_score desc
    try:
        snippets = repo_search_snippets(session, req.q, limit=req.limit)
        snippets = sorted(snippets, key=lambda s: (s.echo_score or 0.0), reverse=True)
    except Exception:
        logging.exception("snippet search failed")
        snippets = []

    # Map snippets to lightweight summaries
    snippet_summaries = [
        {
            "id": s.id,
            "title": s.title,
            "summary": s.summary,
            "echo_score": s.echo_score,
            "success_count": s.success_count,
            "ticket_id": s.ticket_id,
        }
        for s in snippets
    ]

    # Compose a richer answer using snippets and tickets
    answer_text, kb_backed, kb_confidence, mode = build_ask_echo_answer(req.q, snippets, tickets)

    # Append experimental note
    answer_text = answer_text + "\n\nNote: This is experimental AI output — verify details before applying fixes."

    return AskEchoResponse(
        query=req.q,
        answer=answer_text,
        results=[r.model_dump() for r in tickets],
        snippets=snippet_summaries,
        kb_backed=kb_backed,
        kb_confidence=kb_confidence,
        mode=mode,
    )
