from sqlmodel import Session, select

import backend.app.db as db
from .models.ticket import Ticket

SEED_TICKETS = [
    {
        "summary": "Password reset not working",
        "description": "User cannot reset password via portal; reset emails bounce back.",
        "external_key": "GEN-1",
        "source": "seed",
        "project_key": "IT",
        "status": "open",
        "priority": "medium",
    },
    {
        "summary": "Wi-Fi intermittent in warehouse",
        "description": "Devices drop off every 10–15 minutes; observed across APs.",
        "external_key": "NET-2",
        "source": "seed",
        "project_key": "OPS",
        "status": "open",
        "priority": "high",
    },
]


def seed_tickets() -> None:
    db.ensure_engine()
    if db.engine is None:
        raise RuntimeError("Database engine is not initialized")

    with Session(db.engine) as session:
        existing = session.exec(select(Ticket)).first()
        if existing:
            # Already seeded
            return

        for t in SEED_TICKETS:
            ticket = Ticket(**t)
            session.add(ticket)
        session.commit()


def main() -> None:
    # Create DB tables and seed a couple tickets if none exist
    db.init_db()
    seed_tickets()

    # Optional demo seed (idempotent) so Ask Echo has grounding.
    # Opt-in to keep default init small and fast.
    try:
        from scripts.seed_demo_org import seed_demo_org  # type: ignore

        seed_demo_org()
    except Exception:
        pass


if __name__ == "__main__":
    main()
