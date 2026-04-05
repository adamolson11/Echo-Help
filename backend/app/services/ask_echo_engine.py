from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypedDict, cast

from sqlmodel import Session

from ..models.snippets import SolutionSnippet
from ..models.ticket import Ticket
from ..schemas.ask_echo import (
    AskEchoEvidence,
    AskEchoFlywheel,
    AskEchoKBEvidence,
    AskEchoReasoning,
    AskEchoReasoningSnippet,
    AskEchoRecommendation,
    AskEchoRecommendationSource,
    AskEchoReference,
    AskEchoTicketSummary,
)
from .ask_echo_templates import AskEchoTemplates
from .kb_adapter import search_kb_entries
from .kb_confidence_policy import calculate_kb_confidence
from .llm_provider import LLMProvider
from .openai_provider import build_default_llm_provider_from_env
from .ranking_policy import clamp01, rank_snippets, rank_tickets
from .semantic_search import semantic_search_tickets
from .snippet_repository import search_snippets as repo_search_snippets
from .ticket_search import keyword_search_tickets


class AskEchoResponseSchema(TypedDict):
    answer: str
    confidence: float
    sources: list[str]
    reasoning: str


@dataclass(frozen=True)
class AskEchoEngineRequest:
    query: str
    limit: int = 5


@dataclass(frozen=True)
class AskEchoEngineResult:
    response: AskEchoResponseSchema
    answer_kind: str  # "grounded" | "ungrounded"
    mode: str
    kb_backed: bool
    top_ticket_score: float
    references: list[AskEchoReference]
    reasoning: AskEchoReasoning
    ticket_summaries: list[AskEchoTicketSummary]
    snippet_summaries: list[dict]
    features: dict
    evidence: list[AskEchoEvidence]
    kb_evidence: list[AskEchoKBEvidence]
    flywheel: AskEchoFlywheel

    @property
    def answer_text(self) -> str:
        return self.response["answer"]

    @property
    def kb_confidence(self) -> float:
        return float(self.response["confidence"])


def _first_line(text: str | None, max_len: int = 200) -> str:
    if not text:
        return ""
    return (str(text).split("\n")[0])[:max_len]


def _build_kb_answer(
    templates: AskEchoTemplates,
    query: str,
    scored_tickets: list[tuple[float, Ticket]],
    kb_evidence: list[AskEchoKBEvidence] | None = None,
) -> tuple[str, list[AskEchoReference]]:
    bullets: list[str] = []
    refs: list[AskEchoReference] = []

    for kb in (kb_evidence or [])[:2]:
        bullets.append(f"- {kb.title} (KB {kb.entry_id})")

    for score, t in (scored_tickets[:3] if scored_tickets else []):
        ticket_id = getattr(t, "id", None)
        title = (
            getattr(t, "summary", None)
            or getattr(t, "title", None)
            or f"Ticket {ticket_id}"
        )
        snippet = _first_line(getattr(t, "description", ""))
        bullets.append(f"- {title} (Ticket #{ticket_id}): {snippet}")
        if ticket_id is not None:
            refs.append(
                AskEchoReference(
                    ticket_id=int(ticket_id),
                    confidence=float(score) if score is not None else None,
                )
            )

    if bullets:
        return templates.grounded_prefix + "\n".join(bullets), refs

    return templates.grounded_fallback, refs


def _build_general_answer(templates: AskEchoTemplates, query: str) -> tuple[str, list[AskEchoReference]]:
    return templates.ungrounded_answer, []


def _build_response_sources(
    *,
    scored_tickets: Sequence[tuple[float, Ticket]],
    kb_evidence: Sequence[AskEchoKBEvidence],
) -> list[str]:
    sources: list[str] = []

    for kb in kb_evidence[:2]:
        sources.append(f"KB {kb.entry_id}: {kb.title}")

    for _, ticket in scored_tickets[:3]:
        ticket_id = getattr(ticket, "id", None)
        if ticket_id is None:
            continue
        title = getattr(ticket, "summary", None) or getattr(ticket, "title", None) or f"Ticket {ticket_id}"
        sources.append(f"Ticket #{ticket_id}: {title}")

    deduped: list[str] = []
    seen: set[str] = set()
    for source in sources:
        if source in seen:
            continue
        seen.add(source)
        deduped.append(source)
    return deduped


def _build_reasoning_summary(
    *,
    kb_backed: bool,
    kb_evidence: Sequence[AskEchoKBEvidence],
    scored_tickets: Sequence[tuple[float, Ticket]],
    snippets: Sequence[SolutionSnippet],
) -> str:
    if kb_backed:
        parts: list[str] = []
        kb_count = len(kb_evidence[:2])
        ticket_count = len(scored_tickets[:3])
        snippet_count = len(snippets[:3])
        if kb_evidence:
            parts.append(f"{kb_count} KB entr{'y' if kb_count == 1 else 'ies'}")
        if scored_tickets:
            parts.append(f"{ticket_count} related ticket{'s' if ticket_count != 1 else ''}")
        if snippets:
            parts.append(f"{snippet_count} snippet{'s' if snippet_count != 1 else ''}")
        detail = ", ".join(parts) if parts else "available support evidence"
        return f"Grounded answer using {detail}."

    return "Fallback answer because no strong KB-backed match was available."


def _build_structured_response(
    *,
    answer: str,
    kb_confidence: float,
    kb_backed: bool,
    kb_evidence: Sequence[AskEchoKBEvidence],
    scored_tickets: Sequence[tuple[float, Ticket]],
    snippets: Sequence[SolutionSnippet],
) -> AskEchoResponseSchema:
    return {
        "answer": str(answer or "").strip(),
        "confidence": clamp01(float(kb_confidence or 0.0)),
        "sources": _build_response_sources(scored_tickets=scored_tickets, kb_evidence=kb_evidence),
        "reasoning": _build_reasoning_summary(
            kb_backed=kb_backed,
            kb_evidence=kb_evidence,
            scored_tickets=scored_tickets,
            snippets=snippets,
        ),
    }


def _signal_float(signals: Mapping[str, object] | None, key: str) -> float | None:
    if signals is None:
        return None
    value = signals.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _build_ticket_summaries(scored: list[tuple[float, Ticket]]) -> list[AskEchoTicketSummary]:
    tickets = [t for _, t in scored]
    out: list[AskEchoTicketSummary] = []
    for t in tickets:
        if t.id is None:
            continue
        out.append(
            AskEchoTicketSummary(
                id=int(t.id),
                summary=t.summary,
                title=None,
            )
        )
    return out


def _build_snippet_summaries(snippets: Iterable[SolutionSnippet]) -> list[dict]:
    return [
        {
            "id": getattr(s, "id", None),
            "title": getattr(s, "title", None),
            "summary": getattr(s, "summary", None),
            "echo_score": getattr(s, "echo_score", None),
            "success_count": getattr(s, "success_count", None),
            "failure_count": getattr(s, "failure_count", 0),
            "ticket_id": getattr(s, "ticket_id", None),
        }
        for s in snippets
    ]


def _ticket_steps(ticket: Ticket, query: str) -> list[str]:
    ticket_id = getattr(ticket, "id", None)
    return [
        f"Open Ticket #{ticket_id} and confirm it matches the current issue: {query}.",
        "Apply the documented fix or resolution notes from the matching ticket.",
        "Verify the result in the affected environment and note what changed.",
    ]


def _snippet_steps(snippet: SolutionSnippet, query: str) -> list[str]:
    title = getattr(snippet, "title", None) or "the snippet"
    return [
        f"Read {title} and check whether it fits the current issue: {query}.",
        "Execute the steps in order and capture any environment-specific differences.",
        "Confirm the symptom is gone before closing the loop.",
    ]


def _kb_steps(entry: AskEchoKBEvidence, query: str) -> list[str]:
    return [
        f"Open {entry.title} and compare its guidance to the current issue: {query}.",
        "Follow the setup or verification checklist in the KB entry.",
        "If the KB path works, capture the condition that made it the right playbook.",
    ]


def _fallback_steps(query: str) -> list[str]:
    return [
        f"Reproduce the issue and capture the exact error state for: {query}.",
        "Check identity, network, and recent change signals before escalating.",
        "If the issue remains unresolved, document the failed path and next escalation target.",
    ]


def _build_flywheel_recommendations(
    *,
    query: str,
    scored_tickets: Sequence[tuple[float, Ticket]],
    snippets: Sequence[SolutionSnippet],
    kb_evidence: Sequence[AskEchoKBEvidence],
) -> AskEchoFlywheel:
    recommendations: list[AskEchoRecommendation] = []

    if snippets:
        snippet = snippets[0]
        snippet_id = getattr(snippet, "id", None)
        title = getattr(snippet, "title", None) or "Apply the best matching snippet"
        summary = getattr(snippet, "summary", None) or "Use the strongest snippet-backed fix Echo found."
        recommendations.append(
            AskEchoRecommendation(
                id=f"snippet-{snippet_id or 1}",
                title=f"Run the snippet-backed fix: {title}",
                summary=summary,
                rationale="Echo ranked this snippet highest based on prior successful support work.",
                confidence=float(getattr(snippet, "echo_score", 0.0) or 0.0),
                source=AskEchoRecommendationSource(
                    kind="snippet",
                    label=title,
                    snippet_id=int(snippet_id) if snippet_id is not None else None,
                    ticket_id=getattr(snippet, "ticket_id", None),
                ),
                steps=_snippet_steps(snippet, query),
            )
        )

    if scored_tickets:
        score, ticket = scored_tickets[0]
        ticket_id = getattr(ticket, "id", None)
        title = getattr(ticket, "summary", None) or getattr(ticket, "title", None) or f"Ticket #{ticket_id}"
        recommendations.append(
            AskEchoRecommendation(
                id=f"ticket-{ticket_id or 1}",
                title=f"Reuse the fix pattern from Ticket #{ticket_id}",
                summary=title,
                rationale="This ticket is the closest historical match for the current problem.",
                confidence=float(score),
                source=AskEchoRecommendationSource(
                    kind="ticket",
                    label=title,
                    ticket_id=int(ticket_id) if ticket_id is not None else None,
                ),
                steps=_ticket_steps(ticket, query),
            )
        )

    if kb_evidence:
        entry = kb_evidence[0]
        recommendations.append(
            AskEchoRecommendation(
                id=f"kb-{entry.entry_id}",
                title=f"Follow the KB playbook: {entry.title}",
                summary="Use the curated knowledge-base guidance before escalating to a custom investigation.",
                rationale="The knowledge base contains a likely reusable path for this class of issue.",
                confidence=float(entry.score or 0.0),
                source=AskEchoRecommendationSource(
                    kind="kb",
                    label=entry.title,
                    entry_id=entry.entry_id,
                    source_url=entry.source_url,
                ),
                steps=_kb_steps(entry, query),
            )
        )

    fallback_index = 1
    while len(recommendations) < 3:
        recommendations.append(
            AskEchoRecommendation(
                id=f"general-{fallback_index}",
                title="Run a focused diagnostic pass",
                summary="When Echo has partial grounding, use a structured diagnostic path and capture what you learn.",
                rationale="This keeps the loop moving without pretending there is stronger evidence than we have.",
                confidence=0.25,
                source=AskEchoRecommendationSource(
                    kind="general",
                    label="General diagnostic guidance",
                ),
                steps=_fallback_steps(query),
            )
        )
        fallback_index += 1

    return AskEchoFlywheel(
        issue=query,
        recommendations=recommendations[:3],
    )


def build_ask_echo_features(
    *,
    scored_tickets: Sequence[tuple[float, Ticket]],
    snippets: Sequence[SolutionSnippet],
    ticket_signal_evidence: list[dict] | None = None,
) -> dict:
    """Return a stable, JSON-serializable feature dict for offline ML/eval.

    Intentionally does NOT include raw ticket/snippet text.
    """
    scores = [float(score) for score, _ in scored_tickets if score is not None]
    top_ticket_score = float(max(scores) if scores else 0.0)

    top_snippet_echo_score: float = 0.0
    if snippets:
        s0 = snippets[0]
        v = getattr(s0, "echo_score", None)
        top_snippet_echo_score = float(v) if isinstance(v, (int, float)) else 0.0

    return {
        "version": "v1",
        "ticket": {
            "count": int(len(scored_tickets)),
            "top_score": top_ticket_score,
            "signal_evidence": ticket_signal_evidence or [],
        },
        "snippet": {
            "count": int(len(snippets)),
            "top_echo_score": top_snippet_echo_score,
            "top_success_count": int(getattr(snippets[0], "success_count", 0) or 0) if snippets else 0,
            "top_failure_count": int(getattr(snippets[0], "failure_count", 0) or 0) if snippets else 0,
        },
    }


class AskEchoEngine:
    """Pure-ish Ask Echo logic.

    This intentionally separates:
    - retrieval/scoring (tickets + snippets)
    - answer templating (string templates)

    so the "language" part can be swapped for an LLM later without
    rewriting the route, persistence, or tests.
    """

    def __init__(
        self,
        *,
        templates: AskEchoTemplates | None = None,
        kb_threshold: float = 0.6,
        ticket_retriever=None,
        snippet_retriever=None,
        grounding_decider=None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.templates = templates or AskEchoTemplates()
        self.kb_threshold = kb_threshold
        self._ticket_retriever = ticket_retriever
        self._snippet_retriever = snippet_retriever
        self._grounding_decider = grounding_decider
        self._llm_provider = llm_provider or build_default_llm_provider_from_env()

    def _retrieve_tickets(self, *, session: Session, query: str, limit: int):
        if self._ticket_retriever is not None:
            return self._ticket_retriever(session=session, query=query, limit=limit)

        # Prefer semantic search when embeddings are present.
        scored = semantic_search_tickets(session=session, query=query, limit=limit)
        if scored:
            # Apply the central ranking policy for a consistent ordering,
            # but keep the semantic similarity score as the returned score
            # to preserve existing threshold/telemetry semantics.
            tickets = [t for _, t in scored]
            semantic_scores = {
                int(t.id): float(score)
                for (score, t) in scored
                if t.id is not None
            }
            ranked = rank_tickets(
                session,
                candidates=tickets,
                query=query,
                semantic_scores=semantic_scores,
            )
            ordered = []
            for rt in ranked[:limit]:
                tid = getattr(rt.ticket, "id", None)
                sem = float(semantic_scores.get(int(tid), 0.0)) if tid is not None else 0.0
                ordered.append((sem, rt.ticket))
            return ordered

        # Fallback: keyword search so Ask Echo still returns suggestions even
        # when embeddings are missing/unavailable.
        tickets = keyword_search_tickets(session, query=query, limit=limit)
        pseudo_score = 0.65  # above default kb_threshold so we treat these as KB-backed
        return [(pseudo_score, t) for t in tickets]

    def _retrieve_snippets(self, *, session: Session, query: str, limit: int):
        if self._snippet_retriever is not None:
            return self._snippet_retriever(session=session, query=query, limit=limit)
        return repo_search_snippets(session, query, limit=limit)

    def _decide_grounding(self, *, features: dict, has_snippets: bool, max_ticket_score: float) -> bool:
        """Return whether the answer should be treated as KB-backed."""
        if self._grounding_decider is not None:
            return bool(self._grounding_decider(features=features))
        if has_snippets:
            return True
        return bool(max_ticket_score >= self.kb_threshold)

    def run(self, *, session: Session, req: AskEchoEngineRequest) -> AskEchoEngineResult:
        q = (req.query or "").strip()
        if not q:
            raise ValueError("query required")

        scored = self._retrieve_tickets(session=session, query=q, limit=req.limit)
        kb_results = search_kb_entries(session=session, query=q, limit=max(1, min(3, req.limit)))
        kb_evidence = [
            AskEchoKBEvidence(
                entry_id=item.entry.entry_id,
                title=item.entry.title,
                source_system=item.entry.source_system,
                source_url=item.entry.source_url,
                score=float(item.score),
            )
            for item in kb_results
        ]
        ticket_summaries = _build_ticket_summaries([(score, t) for score, t in scored])

        try:
            snippets = self._retrieve_snippets(session=session, query=q, limit=req.limit)
            ranked_snips = rank_snippets(candidates=list(snippets), query=q)
            snippets = [rs.snippet for rs in ranked_snips]
        except Exception:
            logging.exception("snippet search failed")
            snippets = []

        snippet_summaries = _build_snippet_summaries(snippets)

        scores = [float(score) for score, _ in scored if score is not None]
        max_score = max(scores) if scores else 0.0

        semantic_scores: dict[int, float] = {}
        for score, t in scored:
            tid = getattr(t, "id", None)
            if isinstance(tid, int):
                semantic_scores[tid] = float(score)
        ranked_for_evidence = rank_tickets(
            session,
            candidates=[t for _, t in scored],
            query=q,
            semantic_scores=semantic_scores,
        )
        top_ticket_signals = ranked_for_evidence[0].signals if ranked_for_evidence else {}
        ticket_signal_evidence: list[dict] = []
        evidence_rows: list[AskEchoEvidence] = []
        for row in ranked_for_evidence[:3]:
            tid = getattr(row.ticket, "id", None)
            if tid is None:
                continue
            signals = row.signals or {}
            boosts_applied = signals.get("boosts_applied") if isinstance(signals, dict) else []
            quality_label = signals.get("answer_quality_label") if isinstance(signals, dict) else None
            final_score = signals.get("final_score") if isinstance(signals, dict) else None

            normalized_quality_label = cast(
                Literal["good", "bad", "mixed"] | None,
                quality_label if quality_label in {"good", "bad", "mixed"} else None,
            )
            evidence_rows.append(
                AskEchoEvidence(
                    ticket_id=int(tid),
                    external_key=getattr(row.ticket, "external_key", None),
                    answer_quality_label=normalized_quality_label,
                    boosts_applied=[str(x) for x in boosts_applied] if isinstance(boosts_applied, list) else [],
                    final_score=float(final_score) if isinstance(final_score, (int, float)) else None,
                )
            )
            ticket_signal_evidence.append(
                {
                    "ticket_id": int(tid),
                    "external_key": getattr(row.ticket, "external_key", None),
                    "answer_quality_label": quality_label,
                    "boosts_applied": boosts_applied,
                    "signals": row.signals or {},
                }
            )

        features = build_ask_echo_features(
            scored_tickets=scored,
            snippets=snippets,
            ticket_signal_evidence=ticket_signal_evidence,
        )
        features["provider"] = {
            "enabled": self._llm_provider is not None,
            "used": False,
            "mode": None,
            "source_count": 0,
        }

        kb_backed = self._decide_grounding(
            features=features,
            has_snippets=bool(snippets),
            max_ticket_score=float(max_score or 0.0),
        )

        if kb_backed and (snippets or scored):
            answer_text, references = _build_kb_answer(
                self.templates,
                q,
                [(float(s), t) for s, t in scored],
                kb_evidence=kb_evidence,
            )
            mode = "kb_answer"
            top_snip_score = getattr(snippets[0], "echo_score", None) if snippets else None
            kb_confidence = calculate_kb_confidence(
                kb_backed=True,
                top_snippet_echo_score=float(top_snip_score) if top_snip_score is not None else None,
                top_ticket_score=float(max_score or 0.0),
                has_snippets=bool(snippets),
                has_tickets=bool(scored),
                semantic_similarity=_signal_float(top_ticket_signals, "semantic"),
                keyword_overlap=_signal_float(top_ticket_signals, "keyword"),
                recency=_signal_float(top_ticket_signals, "recency"),
            )
        else:
            answer_text, references = _build_general_answer(self.templates, q)
            mode = "general_answer"
            kb_confidence = calculate_kb_confidence(
                kb_backed=False,
                top_snippet_echo_score=None,
                top_ticket_score=float(max_score or 0.0),
                has_snippets=bool(snippets),
                has_tickets=bool(scored),
                semantic_similarity=_signal_float(top_ticket_signals, "semantic"),
                keyword_overlap=_signal_float(top_ticket_signals, "keyword"),
                recency=_signal_float(top_ticket_signals, "recency"),
            )
            if self._llm_provider is not None:
                try:
                    provider_answer = self._llm_provider.generate(
                        problem=q,
                        context={
                            "query": q,
                            "kb_confidence": clamp01(float(kb_confidence or 0.0)),
                            "kb_backed": False,
                            "top_ticket_score": float(max_score or 0.0),
                            "candidate_ticket_titles": [
                                getattr(ticket, "summary", None)
                                or getattr(ticket, "title", None)
                                or f"Ticket #{getattr(ticket, 'id', 'unknown')}"
                                for _, ticket in scored[:3]
                            ],
                            "kb_titles": [entry.title for entry in kb_evidence[:2]],
                            "snippet_titles": [
                                getattr(snippet, "title", None) or "snippet"
                                for snippet in snippets[:3]
                            ],
                            "local_answer": answer_text,
                        },
                    )
                except Exception:
                    logging.exception("llm provider fallback failed")
                else:
                    if provider_answer.answer_text.strip():
                        answer_text = provider_answer.answer_text.strip()
                        features["provider"] = {
                            "enabled": True,
                            "used": True,
                            "mode": provider_answer.mode,
                            "source_count": len(provider_answer.sources or []),
                        }

        answer_kind = "grounded" if kb_backed else "ungrounded"

        # reasoning (snippet candidates)
        candidate_pairs: list[tuple[SolutionSnippet, float]] = []
        for s in snippets:
            score_val = getattr(s, "echo_score", None)
            candidate_pairs.append((s, float(score_val) if score_val is not None else 0.0))

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
                if s.id is not None
            ],
            chosen_snippet_ids=[
                int(s.id) for s in chosen_snippets if s.id is not None
            ],
            echo_score=float(best_score) if best_score is not None else None,
        )

        answer_text = answer_text + self.templates.experimental_note
        response = _build_structured_response(
            answer=answer_text,
            kb_confidence=kb_confidence,
            kb_backed=kb_backed,
            kb_evidence=kb_evidence,
            scored_tickets=[(float(s), t) for s, t in scored],
            snippets=snippets,
        )
        flywheel = _build_flywheel_recommendations(
            query=q,
            scored_tickets=[(float(s), t) for s, t in scored],
            snippets=snippets,
            kb_evidence=kb_evidence,
        )

        return AskEchoEngineResult(
            response=response,
            answer_kind=answer_kind,
            mode=mode,
            kb_backed=kb_backed,
            top_ticket_score=float(max_score or 0.0),
            references=references,
            reasoning=reasoning,
            ticket_summaries=ticket_summaries,
            snippet_summaries=snippet_summaries,
            features=features,
            evidence=evidence_rows,
            kb_evidence=kb_evidence,
            flywheel=flywheel,
        )
