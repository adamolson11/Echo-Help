from sqlmodel import Session, select

from .db import engine, init_db
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
    with Session(engine) as session:
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
    init_db()
    seed_tickets()


if __name__ == "__main__":
    main()
