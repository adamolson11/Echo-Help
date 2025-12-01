from collections import Counter

from sqlmodel import Session, select

from ..models.ticket import Ticket
from ..models.ticket_feedback import TicketFeedback


def get_feedback_patterns(session: Session) -> dict:
    feedback = session.exec(select(TicketFeedback)).all()

    by_ticket = Counter()
    unresolved_by_ticket = Counter()

    for fb in feedback:
        by_ticket[fb.ticket_id] += 1
        if fb.helped is False:
            unresolved_by_ticket[fb.ticket_id] += 1

    tickets = session.exec(select(Ticket)).all()
    ticket_map = {t.id: t for t in tickets}

    def ticket_info(ticket_id: int) -> dict:
        t = ticket_map.get(ticket_id)
        if not t:
            return {"ticket_id": ticket_id}
        return {
            "ticket_id": ticket_id,
            "summary": getattr(t, "summary", getattr(t, "title", "")),
        }

    by_ticket_list = [
        {
            **ticket_info(ticket_id),
            "total_feedback": total,
            "unresolved": unresolved_by_ticket.get(ticket_id, 0),
        }
        for ticket_id, total in by_ticket.most_common()
    ]

    top_unresolved = sorted(by_ticket_list, key=lambda x: x["unresolved"], reverse=True)

    return {
        "total_feedback": len(feedback),
        "by_ticket": by_ticket_list,
        "top_unresolved": top_unresolved[:10],
    }
