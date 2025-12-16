from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from backend.app.db import get_session
from backend.app.models.ticket import Ticket
from backend.app.schemas.ingest import IngestThread
from backend.app.services.ingest import ingest_thread

router = APIRouter(tags=["ingest"])


@router.post("/ingest/thread", response_model=Ticket)
def ingest_thread_endpoint(
    payload: IngestThread, session: Session = Depends(get_session)
):
    # Use the ingest service to create the ticket (and optional feedback).
    ticket = ingest_thread(payload, session)

    # Re-query the DB using the active session to ensure we return a fully
    # populated Ticket instance (avoid occasional SQLModel serialization edge-cases).
    stmt = select(Ticket).where(Ticket.id == ticket.id)
    db_ticket = session.exec(stmt).one()
    # Use model_dump to produce a plain serializable dict
    return db_ticket.model_dump()
