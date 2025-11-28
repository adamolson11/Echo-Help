#!/usr/bin/env python3
"""Backfill embeddings for existing tickets.

Generates embeddings for ticket text (summary + description) and upserts
them into the `embedding` table.
"""
from __future__ import annotations

from sqlmodel import select

from backend.app.db import get_session, init_db
from backend.app.models.embedding import Embedding
from backend.app.models.ticket import Ticket
from backend.app.services.embeddings import MODEL_NAME, embed_text


def build_ticket_text(ticket: Ticket) -> str:
    parts = [ticket.summary or ""]
    if ticket.description:
        parts.append(ticket.description)
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def upsert_ticket_embedding(ticket: Ticket) -> Embedding | None:
    text = build_ticket_text(ticket).strip()
    if not text:
        return None

    vec = embed_text(text)

    with next(get_session()) as session:
        existing = session.exec(select(Embedding).where(Embedding.ticket_id == ticket.id)).first()

        if existing:
            existing.text = text
            existing.vector = vec  # type: ignore[assignment]
            existing.model_name = MODEL_NAME
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing

        emb = Embedding(
            ticket_id=ticket.id,
            text=text,
            vector=vec,  # type: ignore[assignment]
            model_name=MODEL_NAME,
        )
        session.add(emb)
        session.commit()
        session.refresh(emb)
        return emb


def main() -> None:
    init_db()

    with next(get_session()) as session:
        tickets = list(session.exec(select(Ticket)).all())

    print(f"Found {len(tickets)} tickets.")

    count = 0
    for t in tickets:
        if t.id is None:
            continue
        e = upsert_ticket_embedding(t)
        if e is not None:
            count += 1

    print(f"Updated/created embeddings for {count} tickets.")


if __name__ == "__main__":
    main()
