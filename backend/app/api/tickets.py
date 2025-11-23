from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Ticket

router = APIRouter(tags=["tickets"])

@router.get("/tickets")
def list_tickets(session: Session = Depends(get_session)):
    statement = select(Ticket)
    return session.exec(statement).all()

@router.post("/tickets/seed-demo")
def seed_demo(session: Session = Depends(get_session)):
    if session.exec(select(Ticket)).all():
        return {"message": "Tickets already exist"}

    demo = [
        Ticket(
            external_key="DEMO-1",
            source="jira",
            project_key="DEMO",
            summary="User cannot login",
            description="Failed authentication error when attempting to log in.",
            status="Open",
            priority="High",
        ),
        Ticket(
            external_key="DEMO-2",
            source="jira",
            project_key="DEMO",
            summary="VPN disconnecting",
            description="VPN drops connection every 10 minutes.",
            status="Open",
            priority="Medium",
        ),
    ]

    for t in demo:
        session.add(t)
    session.commit()

    return {"message": "Demo tickets added"}
