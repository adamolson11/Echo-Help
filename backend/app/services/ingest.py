from sqlmodel import Session

from backend.app.models.embedding import Embedding
from backend.app.models.ticket import Ticket
from backend.app.models.ticket_feedback import TicketFeedback
from backend.app.schemas.ingest import IngestThread
from backend.app.services.embeddings import MODEL_NAME, embed_text
from backend.app.services.tickets import assign_short_id


def ingest_thread(thread: IngestThread, session: Session) -> Ticket:
    """Create a Ticket from an IngestThread. If resolved, also create a TicketFeedback row.

    This function will also synchronously generate an embedding for the
    created ticket so it is immediately available for semantic search.
    """
    # Combine messages into a description blob
    description = "\n".join(f"[{m.author}] {m.text}" for m in thread.messages)

    ticket = Ticket(
        external_key=thread.external_id,
        source=thread.source,
        project_key=thread.source or "ingest",
        summary=thread.title,
        description=description,
        status="closed" if thread.resolved else "open",
    )

    session.add(ticket)
    session.commit()
    session.refresh(ticket)

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
    try:
        text_for_embedding = f"{ticket.summary}\n\n{ticket.description or ''}"
        vector = embed_text(text_for_embedding)
        embedding = Embedding(
            ticket_id=ticket.id,
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
        feedback = TicketFeedback(
            ticket_id=ticket.id,
            helped=True,
            rating=4,
            query_text=thread.title,
            resolution_notes=thread.resolution_notes or "Resolved via ingest",
        )
        session.add(feedback)
        session.commit()
        session.refresh(feedback)

    return ticket
