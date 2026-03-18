from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal, cast

from sqlmodel import Session

from ..models.snippets import SolutionSnippet
from ..models.ticket import Ticket
from ..schemas.ask_echo import (
    AskEchoEvidence,
    AskEchoKBEvidence,
    AskEchoReasoning,
    AskEchoReasoningSnippet,
    AskEchoReference,
    AskEchoTicketSummary,
)
from .ask_echo_templates import AskEchoTemplates
from .kb_adapter import search_kb_entries
from .kb_confidence_policy import calculate_kb_confidence
from .ranking_policy import rank_snippets, rank_tickets
from .semantic_search import semantic_search_tickets
from .snippet_repository import search_snippets as repo_search_snippets
from .ticket_search import keyword_search_tickets


@dataclass(frozen=True)
class AskEchoEngineRequest:
    query: str
    limit: int = 5


@dataclass(frozen=True)
class AskEchoEngineResult:
    answer_text: str
    answer_kind: str  # "grounded" | "ungrounded"
    mode: str
    kb_backed: bool
    kb_confidence: float
    top_ticket_score: float
    references: list[AskEchoReference]
    reasoning: AskEchoReasoning
    ticket_summaries: list[AskEchoTicketSummary]
    snippet_summaries: list[dict]
    features: dict
    evidence: list[AskEchoEvidence]
    kb_evidence: list[AskEchoKBEvidence]


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
    ) -> None:
        self.templates = templates or AskEchoTemplates()
        self.kb_threshold = kb_threshold
        self._ticket_retriever = ticket_retriever
        self._snippet_retriever = snippet_retriever
        self._grounding_decider = grounding_decider

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
            )

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

        return AskEchoEngineResult(
            answer_text=answer_text,
            answer_kind=answer_kind,
            mode=mode,
            kb_backed=kb_backed,
            kb_confidence=float(kb_confidence or 0.0),
            top_ticket_score=float(max_score or 0.0),
            references=references,
            reasoning=reasoning,
            ticket_summaries=ticket_summaries,
            snippet_summaries=snippet_summaries,
            features=features,
            evidence=evidence_rows,
            kb_evidence=kb_evidence,
        )
