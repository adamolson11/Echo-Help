# ruff: noqa: B008

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc
from sqlmodel import Session, col, select

from backend.app.db import get_session
from backend.app.models.ask_echo_feedback import AskEchoFeedback
from backend.app.models.ask_echo_log import AskEchoLog
from backend.app.schemas.ask_echo import (
    AskEchoRequest,
    AskEchoResponse,
)
from backend.app.schemas.ask_echo_feedback import (
    AskEchoFeedbackCreate,
    AskEchoFeedbackRead,
    AskEchoFeedbackSummaryResponse,
)
from backend.app.schemas.insights import AskEchoLogDetail, AskEchoLogSummary
from backend.app.schemas.snippets import SnippetSearchResult
from backend.app.services.ask_echo_engine import AskEchoEngine, AskEchoEngineRequest
from backend.app.services.embeddings import embeddings_enabled, log_embeddings_disabled_once

router = APIRouter(tags=["ask-echo"])  # will be included with prefix="/api" in main
logger = logging.getLogger("uvicorn.error")


@router.post("/ask-echo/feedback", response_model=AskEchoFeedbackRead)
def submit_ask_echo_feedback(
    payload: AskEchoFeedbackCreate,
    session: Session = Depends(get_session),
) -> AskEchoFeedbackRead:
    log = session.get(AskEchoLog, payload.ask_echo_log_id)
    if not log:
        raise HTTPException(status_code=404, detail="AskEchoLog not found")

    row = AskEchoFeedback(
        ask_echo_log_id=payload.ask_echo_log_id,
        helped=payload.helped,
        notes=(payload.notes.strip() if payload.notes else None),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    if row.id is None:
        raise HTTPException(status_code=500, detail="failed to persist ask-echo feedback")

    return AskEchoFeedbackRead(
        id=row.id,
        ask_echo_log_id=row.ask_echo_log_id,
        helped=row.helped,
        notes=row.notes,
        created_at=row.created_at,
    )


@router.get("/ask-echo/feedback/summary", response_model=AskEchoFeedbackSummaryResponse)
def get_ask_echo_feedback_summary(
    days: int = 30,
    session: Session = Depends(get_session),
) -> AskEchoFeedbackSummaryResponse:
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be positive")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(AskEchoFeedback).where(AskEchoFeedback.created_at >= cutoff)  # type: ignore[attr-defined]
    rows = list(session.exec(stmt).all())

    total = len(rows)
    helped_true = sum(1 for r in rows if r.helped is True)
    helped_false = sum(1 for r in rows if r.helped is False)

    return AskEchoFeedbackSummaryResponse(
        window_days=days,
        total_feedback=total,
        helped_true=helped_true,
        helped_false=helped_false,
    )


@router.post("/ask-echo", response_model=AskEchoResponse)
def ask_echo(
    req: AskEchoRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    if not req.q or not req.q.strip():
        raise HTTPException(status_code=400, detail="query required")

    request_id = str(uuid4())
    source_channel = request.headers.get("x-source-channel") or request.headers.get("x-echo-source")
    embeddings_on = embeddings_enabled()
    if not embeddings_on:
        log_embeddings_disabled_once()
    logger.warning(
        "ask_echo.request id=%s source_channel=%s embeddings_enabled=%s query_len=%s",
        request_id,
        source_channel or "unknown",
        embeddings_on,
        len(req.q.strip()),
    )

    engine = AskEchoEngine()
    try:
        result = engine.run(session=session, req=AskEchoEngineRequest(query=req.q, limit=req.limit))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Persist telemetry log (required for feedback loop).
    # For logging: capture snippet candidate ids/scores.
    refs_count = len(result.references) if result.references is not None else 0
    candidate_data = [
        {"id": c.id, "score": c.score, "title": c.title}
        for c in (result.reasoning.candidate_snippets or [])
    ]
    chosen_ids = list(result.reasoning.chosen_snippet_ids or [])

    log = AskEchoLog(
        query=req.q,
        top_score=float(result.top_ticket_score or 0.0),
        kb_confidence=float(result.kb_confidence or 0.0),
        mode=result.mode,
        references_count=refs_count,
        candidate_snippet_ids_json=(json.dumps(candidate_data) if candidate_data else None),
        chosen_snippet_ids_json=json.dumps(chosen_ids) if chosen_ids else None,
        echo_score=result.reasoning.echo_score,
        reasoning_notes=(
            json.dumps({"features": result.features, "response": result.response})
            if getattr(result, "features", None)
            else json.dumps({"response": result.response})
        ),
    )
    try:
        session.add(log)
        session.commit()
        session.refresh(log)
    except Exception as e:
        logging.exception("failed to persist ask-echo log")
        raise HTTPException(status_code=500, detail="failed to persist ask-echo log") from e

    if log.id is None:
        raise HTTPException(status_code=500, detail="ask-echo log id missing")

    logger.warning(
        "ask_echo.response id=%s ask_echo_log_id=%s mode=%s answer_kind=%s",
        request_id,
        log.id,
        result.mode,
        result.answer_kind,
    )

    # Normalize snippet summaries to the public schema type.
    # (The engine may return dict-shaped summaries for convenience.)
    snippet_summaries: list[SnippetSearchResult] = []
    for item in result.snippet_summaries or []:
        if isinstance(item, SnippetSearchResult):
            snippet_summaries.append(item)
            continue
        if not isinstance(item, dict):
            continue
        try:
            snippet_summaries.append(SnippetSearchResult(**item))
        except Exception:
            continue

    return AskEchoResponse(
        answer_kind=result.answer_kind,  # type: ignore[arg-type]
        ask_echo_log_id=int(log.id),
        query=req.q,
        answer=result.answer_text,
        suggested_tickets=result.ticket_summaries,
        suggested_snippets=snippet_summaries,
        kb_backed=result.kb_backed,
        kb_confidence=result.kb_confidence,
        mode=result.mode,
        references=result.references,
        reasoning=result.reasoning,
        evidence=result.evidence,
        kb_evidence=result.kb_evidence,
    )


@router.get("/ask-echo/logs", response_model=list[AskEchoLogSummary])
def list_ask_echo_logs(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    stmt = (
        select(AskEchoLog)
        .order_by(desc(col(AskEchoLog.created_at)))
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


@router.get("/ask-echo/logs/{log_id}", response_model=AskEchoLogDetail)
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
