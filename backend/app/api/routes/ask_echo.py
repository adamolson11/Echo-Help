import json
import logging
from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlmodel import select

from backend.app.db import get_session
from backend.app.models.ask_echo_log import AskEchoLog
from backend.app.models.ticket import Ticket
from backend.app.schemas.ask_echo import (AskEchoReasoning,
                                          AskEchoReasoningSnippet,
                                          AskEchoReference, AskEchoRequest,
                                          AskEchoResponse)
from backend.app.services.semantic_search import semantic_search_tickets
from backend.app.services.snippet_repository import \
    search_snippets as repo_search_snippets


def _truncate(text: str | None, length: int = 240) -> str:
    if not text:
        return ""
    t = str(text).strip()
    if len(t) <= length:
        return t
    return t[:length].rsplit(" ", 1)[0] + "..."


def build_kb_answer(
    query: str, scored_tickets: List[tuple], snippets: list
) -> tuple[str, List[AskEchoReference]]:
    """Construct a simple KB-grounded answer and return references to tickets.

    Uses top up to 3 tickets from `scored_tickets` (list of (score, Ticket)).
    """
    bullets: List[str] = []
    refs: List[AskEchoReference] = []
    # take top 3
    for score, t in (scored_tickets[:3] if scored_tickets else []):
        ticket_id = getattr(t, "id", None)
        title = (
            getattr(t, "summary", None)
            or getattr(t, "title", None)
            or f"Ticket {ticket_id}"
        )
        snippet = (getattr(t, "description", "") or "").split("\n")[0][:200]
        bullets.append(f"- {title} (Ticket #{ticket_id}): {snippet}")
        if ticket_id is not None:
            refs.append(
                AskEchoReference(
                    ticket_id=int(ticket_id),
                    confidence=float(score) if score is not None else None,
                )
            )

    if bullets:
        answer = (
            "Based on your past tickets, here are the most relevant related issues:\n"
            + "\n".join(bullets)
        )
    else:
        answer = "I found some tickets that may be related, but couldn't format them clearly."

    return answer, refs


def build_general_answer(query: str) -> tuple[str, List[AskEchoReference]]:
    answer = (
        "I couldn't find any matching tickets or prior solutions in your history for this question. "
        "Here's general guidance based on typical IT issues, but it's not specific to your environment."
    )
    return answer, []


router = APIRouter(tags=["ask-echo"])  # will be included with prefix="/api" in main


@router.post("/ask-echo", response_model=AskEchoResponse)
def ask_echo(req: AskEchoRequest, session: Session = Depends(get_session)):
    if not req.q or not req.q.strip():
        raise HTTPException(status_code=400, detail="query required")

    # Run semantic search to gather top related tickets (score, Ticket)
    scored = semantic_search_tickets(session=session, query=req.q, limit=req.limit)

    # Extract tickets for compatibility
    tickets = [t for _, t in scored]

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
            "failure_count": getattr(s, "failure_count", 0),
            "ticket_id": getattr(s, "ticket_id", None),
        }
        for s in snippets
    ]

    # Decide whether we have KB grounding. Prefer snippet evidence; otherwise fall back to ticket similarity.
    scores = [float(score) for score, _ in scored if score is not None]
    max_score = max(scores) if scores else 0.0
    KB_THRESHOLD = 0.6

    if snippets:
        # KB-backed because we found relevant snippets
        answer_text, references = build_kb_answer(req.q, scored, snippets)
        mode = "kb_answer"
        kb_backed = True
        kb_confidence = (
            float(snippets[0].echo_score)
            if snippets and getattr(snippets[0], "echo_score", None) is not None
            else (max_score if max_score else 0.0)
        )
    elif max_score >= KB_THRESHOLD and scored:
        # No snippets, but strong ticket match
        answer_text, references = build_kb_answer(req.q, scored, snippets)
        mode = "kb_answer"
        kb_backed = True
        kb_confidence = float(max_score)
    else:
        # No KB data and no strong ticket match — general guidance
        answer_text, references = build_general_answer(req.q)
        mode = "general_answer"
        kb_backed = False
        kb_confidence = 0.0

    # Append experimental note
    answer_text = (
        answer_text
        + "\n\nNote: This is experimental AI output — verify details before applying fixes."
    )

    # Build reasoning data for logging and response
    candidate_pairs = []
    for s in snippets:
        score_val = getattr(s, "echo_score", None)
        if score_val is None:
            score_val = 0.0
        candidate_pairs.append((s, float(score_val)))

    chosen_snippets = snippets if snippets else []
    best_score = max((score for _, score in candidate_pairs), default=None)

    reasoning = AskEchoReasoning(
        candidate_snippets=[
            AskEchoReasoningSnippet(
                id=int(s.id),
                title=getattr(s, "title", None),
                score=float(score),
            )
            for (s, score) in candidate_pairs
            if getattr(s, "id", None) is not None
        ],
        chosen_snippet_ids=[
            int(s.id) for s in chosen_snippets if getattr(s, "id", None) is not None
        ],
        echo_score=float(best_score) if best_score is not None else None,
    )

    # Persist a small telemetry log for tuning KB threshold and behavior
    try:
        top_score_val = float(max_score) if "max_score" in locals() else 0.0
        refs_count = len(references) if references is not None else 0
        candidate_data = [
            {"id": int(s.id), "score": float(score)}
            for (s, score) in candidate_pairs
            if getattr(s, "id", None) is not None
        ]

        chosen_ids = [
            int(s.id) for s in chosen_snippets if getattr(s, "id", None) is not None
        ]

        log = AskEchoLog(
            query=req.q,
            top_score=top_score_val,
            kb_confidence=float(kb_confidence or 0.0),
            mode=mode,
            references_count=refs_count,
            candidate_snippet_ids_json=(
                json.dumps(candidate_data) if candidate_data else None
            ),
            chosen_snippet_ids_json=json.dumps(chosen_ids) if chosen_ids else None,
            echo_score=float(best_score) if best_score is not None else None,
            reasoning_notes=None,
        )
        try:
            session.add(log)
            session.commit()
        except Exception:
            # be defensive: if logging fails, don't break Ask Echo
            logging.exception("failed to persist ask-echo log")
    except Exception:
        # swallow any logging errors
        logging.exception("ask-echo logging error")

    return AskEchoResponse(
        query=req.q,
        answer=answer_text,
        results=[r.model_dump() for r in tickets],
        snippets=snippet_summaries,
        kb_backed=kb_backed,
        kb_confidence=kb_confidence,
        mode=mode,
        references=references,
        reasoning=reasoning,
    )


@router.get("/ask-echo/logs")
def list_ask_echo_logs(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    stmt = (
        select(AskEchoLog)
        .order_by(AskEchoLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    logs = session.exec(stmt).all()

    return [
        {
            "id": log.id,
            "query_text": log.query,
            "ticket_id": None,
            "echo_score": log.echo_score,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/ask-echo/logs/{log_id}")
def get_ask_echo_log(
    log_id: int,
    session: Session = Depends(get_session),
):
    log = session.get(AskEchoLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="AskEchoLog not found")

    try:
        candidate_data = (
            json.loads(log.candidate_snippet_ids_json)
            if log.candidate_snippet_ids_json
            else []
        )
    except json.JSONDecodeError:
        candidate_data = []

    try:
        chosen_ids = (
            json.loads(log.chosen_snippet_ids_json)
            if log.chosen_snippet_ids_json
            else []
        )
    except json.JSONDecodeError:
        chosen_ids = []

    # Normalize candidate snippets into id/score/title shape if needed
    norm_candidates = []
    for item in candidate_data:
        if not isinstance(item, dict):
            continue
        cid = item.get("id")
        score = item.get("score")
        title = item.get("title")
        if cid is None:
            continue
        norm_candidates.append({"id": cid, "score": score, "title": title})

    return {
        "id": log.id,
        "query_text": log.query,
        "answer_text": "",
        "ticket_id": None,
        "echo_score": log.echo_score,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "reasoning": {
            "candidate_snippets": norm_candidates,
            "chosen_snippet_ids": chosen_ids,
        },
        "reasoning_notes": log.reasoning_notes,
    }
