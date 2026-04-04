# ruff: noqa: B008

from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.app.db import get_session
from backend.app.models.ask_echo_feedback import AskEchoFeedback
from backend.app.models.ask_echo_log import AskEchoLog
from backend.app.models.ticket_feedback import TicketFeedback
from backend.app.schemas.flywheel import (
    FlywheelContract,
    FlywheelIssue,
    FlywheelOutcomeRequest,
    FlywheelOutcomeResponse,
    FlywheelRecommendation,
    FlywheelRecommendRequest,
    FlywheelRecommendResponse,
    FlywheelSavedOutcome,
    FlywheelState,
    FlywheelStep,
)
from backend.app.services.ask_echo_engine import AskEchoEngine, AskEchoEngineRequest
from backend.app.services.embeddings import embeddings_enabled, log_embeddings_disabled_once
from backend.app.services.feedback import (
    apply_feedback_analytics,
    apply_user_feedback,
    build_feedback_analytics,
)

router = APIRouter(prefix="/flywheel", tags=["flywheel"])
DEFAULT_TEXT_TRUNCATE_LENGTH = 220


def _contract() -> FlywheelContract:
    return FlywheelContract(
        in_scope=[
            "Capture one operator problem statement",
            "Return exactly three recommended next actions",
            "Show ordered execution steps for the selected action",
            "Capture the outcome and reusable learning in one save",
        ],
        deferred=[
            "Automated branching into multiple loops",
            "Multi-user assignment or approvals",
            "Mobile-specific UI",
            "Adaptive recommendations based on partial step telemetry",
        ],
        acceptance_criteria=[
            "The issue, 3 options, selected steps, outcome, and saved learning are visible in one flow",
            "The flow persists feedback for the originating Ask Echo recommendation",
            "A reusable learning note can be stored without leaving the wedge",
        ],
    )


def _build_states(
    current: Literal["input", "recommend", "execute", "capture", "store"],
) -> list[FlywheelState]:
    order: list[Literal["input", "recommend", "execute", "capture", "store"]] = [
        "input",
        "recommend",
        "execute",
        "capture",
        "store",
    ]
    labels = {
        "input": "Input",
        "recommend": "Recommend 3 options",
        "execute": "Execute selected action",
        "capture": "Capture outcome",
        "store": "Store learning",
    }
    current_index = order.index(current)
    states: list[FlywheelState] = []
    for idx, state_id in enumerate(order):
        status: Literal["complete", "current", "upcoming"] = "upcoming"
        if idx < current_index:
            status = "complete"
        elif idx == current_index:
            status = "current"
        states.append(FlywheelState(id=state_id, label=labels[state_id], status=status))
    return states


def _first_sentence(text: str) -> str:
    value = " ".join(text.split()).strip()
    if not value:
        return "No grounded answer was available, so use the captured evidence to decide the next move."
    for punct in ".!?":
        idx = value.find(punct)
        if idx != -1:
            return value[: idx + 1]
    return value


def _clip(text: str, limit: int = DEFAULT_TEXT_TRUNCATE_LENGTH) -> str:
    value = " ".join(text.split()).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _persist_ask_echo_log(
    *,
    session: Session,
    problem: str,
    result,
) -> AskEchoLog:
    refs_count = len(result.references) if result.references is not None else 0
    candidate_data = [
        {"id": c.id, "score": c.score, "title": c.title}
        for c in (result.reasoning.candidate_snippets or [])
    ]
    chosen_ids = list(result.reasoning.chosen_snippet_ids or [])
    response_sources = list(result.response["sources"])
    analytics = build_feedback_analytics(
        answer=result.answer_text,
        confidence=result.kb_confidence,
        sources=response_sources,
        reasoning=result.response["reasoning"],
        mode=result.mode,
    )
    reasoning_notes_payload = {
        "features": result.features,
        "response": result.response,
        "analytics": {
            "source_count": analytics["source_count"],
            "sources": response_sources,
            "low_confidence": analytics["low_confidence"],
            "no_sources": analytics["no_sources"],
            "fallback_only": analytics["fallback_only"],
            "feedback_status": analytics["feedback_status"],
            "feedback_rating": analytics["feedback_rating"],
        },
        "flywheel_problem": problem,
    }
    log = AskEchoLog(
        query=problem,
        answer_text=analytics["answer_text"],
        top_score=float(result.top_ticket_score or 0.0),
        kb_confidence=float(result.kb_confidence or 0.0),
        mode=result.mode,
        references_count=refs_count,
        source_count=analytics["source_count"],
        reasoning_summary=analytics["reasoning_summary"],
        low_confidence=analytics["low_confidence"],
        no_sources=analytics["no_sources"],
        fallback_only=analytics["fallback_only"],
        feedback_status=analytics["feedback_status"],
        feedback_rating=analytics["feedback_rating"],
        candidate_snippet_ids_json=(json.dumps(candidate_data) if candidate_data else None),
        chosen_snippet_ids_json=(json.dumps(chosen_ids) if chosen_ids else None),
        echo_score=result.reasoning.echo_score,
        reasoning_notes=json.dumps(reasoning_notes_payload),
    )
    apply_feedback_analytics(log=log, analytics=analytics)
    session.add(log)
    session.commit()
    session.refresh(log)
    if log.id is None:
        raise HTTPException(status_code=500, detail="flywheel ask-echo log id missing")
    return log


def _build_recommendations(problem: str, result, ask_echo_log_id: int) -> list[FlywheelRecommendation]:
    top_ticket_id = result.references[0].ticket_id if result.references else None
    top_ticket = result.ticket_summaries[0] if result.ticket_summaries else None
    top_snippet = result.snippet_summaries[0] if result.snippet_summaries else None
    top_kb = result.kb_evidence[0] if result.kb_evidence else None
    answer_summary = _first_sentence(result.answer_text)

    evidence_label = "Ask Echo answer"
    if top_snippet:
        evidence_label = f"Snippet · {top_snippet.title}"
    elif top_kb:
        evidence_label = f"KB · {top_kb.title}"
    elif top_ticket and (top_ticket.title or top_ticket.summary):
        evidence_label = f"Ticket · {top_ticket.title or top_ticket.summary}"

    compare_label = "Closest prior case"
    if top_ticket and (top_ticket.title or top_ticket.summary):
        compare_label = f"Ticket #{top_ticket.id} · {top_ticket.title or top_ticket.summary}"
    elif top_snippet:
        compare_label = f"Snippet · {top_snippet.title}"

    return [
        FlywheelRecommendation(
            id="apply-grounded-fix",
            title="Apply the best grounded fix",
            summary=_clip(answer_summary),
            rationale="This option turns the highest-confidence Echo answer into the first action to try.",
            source_label=evidence_label,
            confidence=float(result.kb_confidence or 0.0),
            ticket_id=top_ticket_id,
            steps=[
                FlywheelStep(
                    id="review-signal",
                    title="Review the grounded signal",
                    instruction=f"Read the top answer and source for '{problem}' before acting.",
                    expected_signal="You can explain why this is the strongest first move.",
                ),
                FlywheelStep(
                    id="apply-fix",
                    title="Apply the recommended fix",
                    instruction=_clip(result.answer_text or "Apply the top recommended remediation path."),
                    expected_signal="The issue changes state or the symptom narrows.",
                ),
                FlywheelStep(
                    id="verify-fix",
                    title="Verify the original symptom",
                    instruction="Re-run the failing workflow and confirm whether the user-facing problem improved.",
                    expected_signal="You can mark the issue resolved, partial, or blocked with evidence.",
                ),
            ],
        ),
        FlywheelRecommendation(
            id="compare-similar-case",
            title="Compare against the closest prior case",
            summary="Use the nearest ticket or snippet match to confirm scope before investing in deeper work.",
            rationale="This option is safest when the operator wants more evidence before changing the environment.",
            source_label=compare_label,
            confidence=float(result.references[0].confidence or 0.0) if result.references else None,
            ticket_id=top_ticket_id,
            steps=[
                FlywheelStep(
                    id="match-context",
                    title="Match context",
                    instruction="Compare the current issue with the closest stored case, including environment and severity.",
                    expected_signal="You know whether this is truly the same failure mode.",
                ),
                FlywheelStep(
                    id="run-diagnostic",
                    title="Run the nearest diagnostic",
                    instruction="Execute the most relevant diagnostic or repro step from the matched case before changing anything else.",
                    expected_signal="You collect one clear observation that confirms or rejects the match.",
                ),
                FlywheelStep(
                    id="decide-next-move",
                    title="Decide the next move",
                    instruction="Either apply the proven fix or switch to escalation with the evidence you gathered.",
                    expected_signal="The next operator action is justified by observed evidence, not guesswork.",
                ),
            ],
        ),
        FlywheelRecommendation(
            id="capture-learning",
            title="Capture evidence for the next loop",
            summary="If the first fix is unclear, turn this issue into a reusable learning artifact instead of losing the context.",
            rationale="This option keeps the wedge moving even when no grounded fix is immediately decisive.",
            source_label=f"Ask Echo log #{ask_echo_log_id}",
            confidence=None,
            ticket_id=top_ticket_id,
            steps=[
                FlywheelStep(
                    id="record-attempt",
                    title="Record what you tried",
                    instruction="Write down the exact action, command, or decision you attempted.",
                    expected_signal="Another operator can replay your move without asking for missing context.",
                ),
                FlywheelStep(
                    id="record-outcome",
                    title="Capture the outcome",
                    instruction="Describe what changed, what did not change, and any blocker that stopped progress.",
                    expected_signal="The wedge has enough data to distinguish resolved, follow-up, and blocked outcomes.",
                ),
                FlywheelStep(
                    id="save-learning",
                    title="Save reusable learning",
                    instruction="Store one concise learning that should influence the next recommendation for a similar issue.",
                    expected_signal="Future operators inherit a reusable note instead of repeating the same dead end.",
                ),
            ],
        ),
    ]


@router.post("/recommend", response_model=FlywheelRecommendResponse)
def recommend_flywheel_actions(
    payload: FlywheelRecommendRequest,
    session: Session = Depends(get_session),
) -> FlywheelRecommendResponse:
    problem = payload.problem.strip()
    if not problem:
        raise HTTPException(status_code=400, detail="problem required")

    if not embeddings_enabled():
        log_embeddings_disabled_once()

    engine = AskEchoEngine()
    try:
        result = engine.run(session=session, req=AskEchoEngineRequest(query=problem, limit=5))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log = _persist_ask_echo_log(session=session, problem=problem, result=result)
    ask_echo_log_id = log.id
    if ask_echo_log_id is None:
        raise HTTPException(status_code=500, detail="flywheel ask-echo log id missing")
    recommendations = _build_recommendations(problem, result, ask_echo_log_id)
    top_ticket_id = result.references[0].ticket_id if result.references else None
    source_count = (len(result.references) if result.references else 0) + len(result.kb_evidence or [])

    return FlywheelRecommendResponse(
        issue=FlywheelIssue(
            problem=problem,
            normalized_problem=" ".join(problem.lower().split()),
            ask_echo_log_id=ask_echo_log_id,
            answer=result.answer_text,
            mode=result.mode,
            confidence=float(result.kb_confidence or 0.0),
            source_count=source_count,
            top_ticket_id=top_ticket_id,
        ),
        states=_build_states("recommend"),
        recommendations=recommendations,
        contract=_contract(),
    )


@router.post("/outcome", response_model=FlywheelOutcomeResponse)
def save_flywheel_outcome(
    payload: FlywheelOutcomeRequest,
    session: Session = Depends(get_session),
) -> FlywheelOutcomeResponse:
    log = session.get(AskEchoLog, payload.ask_echo_log_id)
    if not log:
        raise HTTPException(status_code=404, detail="AskEchoLog not found")

    helped = payload.outcome_status == "resolved"
    learning_summary = (
        payload.reusable_learning.strip()
        if payload.reusable_learning and payload.reusable_learning.strip()
        else f"{payload.recommendation_title} → {payload.outcome_status.replace('_', ' ')}"
    )
    step_summary = ", ".join(payload.completed_step_ids) if payload.completed_step_ids else "none"
    note_parts = [
        f"Problem: {payload.problem.strip()}",
        f"Recommendation: {payload.recommendation_title.strip()} ({payload.recommendation_id.strip()})",
        f"Outcome: {payload.outcome_status}",
        f"Completed steps: {step_summary}",
    ]
    if payload.execution_notes and payload.execution_notes.strip():
        note_parts.append(f"Execution notes: {payload.execution_notes.strip()}")
    if payload.reusable_learning and payload.reusable_learning.strip():
        note_parts.append(f"Reusable learning: {payload.reusable_learning.strip()}")
    saved_notes = "\n".join(note_parts)

    ask_feedback = AskEchoFeedback(
        ask_echo_log_id=payload.ask_echo_log_id,
        helped=helped,
        notes=saved_notes,
    )
    apply_user_feedback(log=log, helped=helped)
    session.add(ask_feedback)
    session.add(log)
    session.commit()
    session.refresh(ask_feedback)
    if ask_feedback.id is None:
        raise HTTPException(status_code=500, detail="failed to persist flywheel outcome")

    ticket_feedback_id: int | None = None
    if payload.ticket_id is not None:
        ticket_feedback = TicketFeedback(
            ticket_id=payload.ticket_id,
            query_text=payload.problem.strip(),
            rating=5 if helped else 2,
            helped=helped,
            resolution_notes=saved_notes,
        )
        session.add(ticket_feedback)
        session.commit()
        session.refresh(ticket_feedback)
        ticket_feedback_id = ticket_feedback.id

    return FlywheelOutcomeResponse(
        saved=FlywheelSavedOutcome(
            ask_echo_feedback_id=int(ask_feedback.id),
            ticket_feedback_id=ticket_feedback_id,
            helped=helped,
            learning_summary=learning_summary,
        ),
        states=_build_states("store"),
    )
