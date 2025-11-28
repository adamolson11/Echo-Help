from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.schemas.ask_echo import AskEchoRequest, AskEchoResponse
from backend.app.services.semantic_search import semantic_search_tickets
from backend.app.db import get_session
from backend.app.models.ticket import Ticket
import logging

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

    return AskEchoResponse(query=req.q, answer=answer, results=[r.model_dump() for r in tickets])
