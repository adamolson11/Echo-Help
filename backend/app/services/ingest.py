from typing import cast

from sqlmodel import Session, select

from backend.app.models.embedding import Embedding
from backend.app.models.ticket import Ticket
from backend.app.models.ticket_feedback import TicketFeedback
from backend.app.schemas.ingest import IngestThread
from backend.app.services.embeddings import (
    MODEL_NAME,
    embed_text,
    embeddings_enabled,
    log_embeddings_disabled_once,
)
from backend.app.services.findings import emit_ticket_draft, normalize_ingest_thread
from backend.app.services.tickets import assign_short_id


def _single_embedding_vector(vector: list[float] | list[list[float]]) -> list[float]:
    if vector and isinstance(vector[0], list):
        return cast(list[float], vector[0])
    return cast(list[float], vector)


def ingest_thread(thread: IngestThread, session: Session) -> Ticket:
    """Create a Ticket from an IngestThread. If resolved, also create a TicketFeedback row.

    This function will also synchronously generate an embedding for the
    created ticket so it is immediately available for semantic search.
    """
    finding = normalize_ingest_thread(thread)
    ticket_draft = emit_ticket_draft(finding)
    derived_tags = [
        f"finding:{finding.category}",
        f"severity:{finding.severity}",
        f"status:{finding.status}",
    ]

    # Idempotency: if we've already ingested this external_id, update the existing
    # Ticket instead of creating a duplicate.
    existing = session.exec(
        select(Ticket).where(Ticket.external_key == thread.external_id)
    ).first()

    if existing is None:
        ticket = Ticket(
            external_key=ticket_draft.external_key or thread.external_id,
            source=ticket_draft.source,
            project_key=ticket_draft.project_key,
            summary=ticket_draft.summary,
            description=ticket_draft.description,
            product_area=finding.product_area,
            severity=finding.severity,
            tags=derived_tags,
            priority=ticket_draft.priority,
            status=ticket_draft.status,
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
    else:
        ticket = existing
        # Keep ingest safe and repeatable: update fields to the latest payload.
        ticket.source = ticket_draft.source
        ticket.project_key = ticket_draft.project_key
        ticket.summary = ticket_draft.summary
        ticket.description = ticket_draft.description
        ticket.product_area = finding.product_area
        ticket.severity = finding.severity
        ticket.tags = derived_tags
        ticket.priority = ticket_draft.priority
        ticket.status = ticket_draft.status
        session.add(ticket)
        session.commit()
        session.refresh(ticket)

    assert ticket.id is not None
    ticket_id = ticket.id

    # Assign a human-friendly short_id for KB use (E-TKT-0001)
    try:
        ticket = assign_short_id(ticket, session)
    except Exception:
        # don't fail ingest on short_id assignment issues
        pass

    # Populate body_md with a minimal Markdown representation
    if not ticket.body_md:
        ticket.body_md = f"# {ticket.summary}\n\n{ticket.description}\n"
        session.add(ticket)
        session.commit()
        session.refresh(ticket)

    # Create an embedding for this ticket so semantic-search sees it immediately.
    # Idempotency: only create if one doesn't already exist.
    try:
        existing_embedding = session.exec(
            select(Embedding).where(Embedding.ticket_id == ticket_id)
        ).first()
        if existing_embedding is None:
            if not embeddings_enabled():
                log_embeddings_disabled_once()
            text_for_embedding = f"{ticket.summary}\n\n{ticket.description or ''}"
            vector = _single_embedding_vector(embed_text(text_for_embedding))
            embedding = Embedding(
                ticket_id=ticket_id,
                text=text_for_embedding,
                vector=vector,
                model_name=MODEL_NAME,
            )
            session.add(embedding)
            session.commit()
            session.refresh(embedding)
    except Exception:
        # Don't let embedding failures block ingest; log or handle later.
        # For now, silently continue.
        pass

    if thread.resolved:
        # Idempotency: don't create duplicate ingest feedback for the same ticket.
        existing_feedback = session.exec(
            select(TicketFeedback).where(
                TicketFeedback.ticket_id == ticket_id,
                TicketFeedback.query_text == thread.title,
                TicketFeedback.helped == True,  # noqa: E712
            )
        ).first()

        if existing_feedback is None:
            feedback = TicketFeedback(
                ticket_id=ticket_id,
                helped=True,
                rating=4,
                query_text=thread.title,
                resolution_notes=thread.resolution_notes or "Resolved via ingest",
            )
            session.add(feedback)
            session.commit()
            session.refresh(feedback)

    return ticket
