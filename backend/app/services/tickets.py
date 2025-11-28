from sqlmodel import Session, select
from backend.app.models.ticket import Ticket


def get_next_short_id(session: Session) -> str:
    """Return the next short_id in the sequence 'E-TKT-0001'.

    This is a simple, best-effort generator suitable for low-concurrency
    development use. It scans existing short_ids and picks the next number.
    """
    rows = session.exec(select(Ticket.short_id)).all()
    maxn = 0
    for s in rows:
        if not s:
            continue
        if isinstance(s, (list, tuple)):
            # some adapters may return Row objects; handle defensively
            s = s[0] if s else None
        try:
            if s.startswith("E-TKT-"):
                n = int(s.split("-")[-1])
                if n > maxn:
                    maxn = n
        except Exception:
            continue
    nextn = maxn + 1
    return f"E-TKT-{nextn:04d}"


def assign_short_id(ticket: Ticket, session: Session) -> Ticket:
    if ticket.short_id:
        return ticket
    sid = get_next_short_id(session)
    ticket.short_id = sid
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket
