import json

from sqlmodel import Session, select

import backend.app.db as db
from backend.app.models import Embedding, Ticket
from backend.app.services.embeddings import MODEL_NAME, embed_text


def get_ticket_embedding_text(ticket: Ticket) -> str:
    parts: list[str] = []
    if ticket.summary:
        parts.append(ticket.summary)
    if ticket.description:
        parts.append(ticket.description)
    return "\n\n".join(parts)


def backfill_ticket_embeddings():
    db.ensure_engine()
    if db.engine is None:
        raise RuntimeError("Database engine is not initialized")

    with Session(db.engine) as session:
        tickets = session.exec(select(Ticket)).all()
        print(f"Found {len(tickets)} tickets")
        for ticket in tickets:
            existing = session.exec(
                select(Embedding).where(
                    Embedding.object_type == "ticket",
                    Embedding.object_id == ticket.id,
                    Embedding.model_name == MODEL_NAME,
                )
            ).first()
            if existing:
                continue
            text = get_ticket_embedding_text(ticket)
            if not text.strip():
                continue
            vec = embed_text(text)
            emb = Embedding(
                object_type="ticket",
                object_id=ticket.id,
                model_name=MODEL_NAME,
                vector_json=json.dumps(vec),
            )
            session.add(emb)
        session.commit()
        print("Backfill complete.")


if __name__ == "__main__":
    backfill_ticket_embeddings()
