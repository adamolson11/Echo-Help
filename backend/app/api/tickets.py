# ruff: noqa: E501,B008
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Ticket
from ..schemas.common import MessageResponse
from ..schemas.tickets import TicketCreateRequest
from ..services.tickets import get_next_short_id

router = APIRouter(tags=["tickets"])


@router.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreateRequest, session: Session = Depends(get_session)) -> Ticket:
    summary = payload.summary.strip()
    description = payload.description.strip()
    source = payload.source.strip() or "manual"
    project_key = payload.project_key.strip().upper() or "IT"
    priority = payload.priority.strip() if isinstance(payload.priority, str) else None

    if not summary:
        raise HTTPException(status_code=422, detail="Summary is required")
    if not description:
        raise HTTPException(status_code=422, detail="Description is required")

    now = datetime.now(timezone.utc)
    short_id = get_next_short_id(session)
    ticket = Ticket(
        short_id=short_id,
        key=short_id,
        external_key=short_id,
        source=source,
        source_system="manual-ui",
        project_key=project_key,
        summary=summary,
        description=description,
        status="open",
        priority=priority or None,
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket


@router.get("/tickets", response_model=list[Ticket])
def list_tickets(session: Session = Depends(get_session),) -> list[Ticket]:
    statement = select(Ticket)
    return list(session.exec(statement).all())


@router.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: int, session: Session = Depends(get_session)) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/tickets/seed-demo", response_model=MessageResponse)
def seed_demo(session: Session = Depends(get_session)) -> MessageResponse:
    if session.exec(select(Ticket)).all():
        return MessageResponse(message="Tickets already exist")

    now = datetime.now(timezone.utc)
    demo = [
        Ticket(
            external_key="INC-1001",
            source="zendesk",
            project_key="IT",
            summary="User unable to log in after password reset",
            description="Customer reports that after resetting the password, the system continues to say 'incorrect password'. User confirms receiving reset email.",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1002",
            source="zendesk",
            project_key="IT",
            summary="VPN disconnects every few minutes",
            description="User states VPN connection drops intermittently, especially when switching applications. No local network problems reported.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1003",
            source="zendesk",
            project_key="IT",
            summary="Cannot access dashboard analytics",
            description="User receives blank screen when opening the analytics dashboard. Browser refresh does not fix. Works for other users.",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1004",
            source="zendesk",
            project_key="IT",
            summary="2FA code not being delivered",
            description="User reports that two-factor authentication text codes are not arriving. Email verification still works.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1005",
            source="zendesk",
            project_key="IT",
            summary="Application freezes on startup",
            description="The desktop client hangs on the loading screen for more than 2 minutes. Logs show repeated connection attempts.",
            status="in_progress",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1006",
            source="zendesk",
            project_key="IT",
            summary="Email notifications not sending",
            description="Customer reports no email alerts are being delivered for ticket updates. Checked spam folder, nothing there.",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1007",
            source="zendesk",
            project_key="IT",
            summary="Slow loading times on main page",
            description="User experiences extremely slow load times specifically on the homepage. Other pages function normally.",
            status="open",
            priority="low",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1008",
            source="zendesk",
            project_key="IT",
            summary="MFA app generates invalid codes",
            description="User's Authenticator app produces codes that are always rejected. Device clock is slightly off-sync.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1009",
            source="zendesk",
            project_key="IT",
            summary="Search bar returns no results",
            description="Search function returns zero hits even for known items. Possibly related to indexing job failure.",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1010",
            source="zendesk",
            project_key="IT",
            summary="User cannot upload files",
            description="Upload attempt ends with error: 'File cannot be processed at this time'. Fails for all file types.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1011",
            source="zendesk",
            project_key="IT",
            summary="Report generation stuck in queue",
            description="Customer's scheduled report has been pending for over 6 hours. Other users' reports are generating normally.",
            status="in_progress",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1012",
            source="zendesk",
            project_key="IT",
            summary="Session expires too early",
            description="User is being logged out after 5 minutes of inactivity—even though organization setting is 60 minutes.",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1013",
            source="zendesk",
            project_key="IT",
            summary="Cannot install update",
            description="Client installer fails with error code 0x87 during update step. User tried restarting.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1014",
            source="zendesk",
            project_key="IT",
            summary="“Insufficient permissions” error when editing profile",
            description="User cannot edit their own profile settings. Backend logs show permission mismatch.",
            status="open",
            priority="low",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1015",
            source="zendesk",
            project_key="IT",
            summary="Payment method cannot be updated",
            description="Billing page returns 500 error on submit. Logs show issue communicating with payment processor.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1016",
            source="zendesk",
            project_key="IT",
            summary="Push notifications delayed",
            description="Mobile app push alerts arrive 15–20 minutes late. Issue persists on Wi-Fi and LTE.",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1017",
            source="zendesk",
            project_key="IT",
            summary="User unable to download CSV export",
            description="Download attempt returns corrupted CSV file. Other formats export correctly.",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1018",
            source="zendesk",
            project_key="IT",
            summary="API key not recognized",
            description="Customer reports new API key returns 401 unauthorized. Key was regenerated earlier today.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1019",
            source="zendesk",
            project_key="IT",
            summary="Dropdown menus not responding",
            description="UI dropdowns do not open on click. Console logs show missing JS bundle.",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1020",
            source="zendesk",
            project_key="IT",
            summary="Webhooks firing multiple times",
            description="Customer receives duplicate webhook events for single update. Logs show repeated retries.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1021",
            source="zendesk",
            project_key="IT",
            summary="User receives 'account locked' message",
            description="Customer account locked after repeated failed logins. Unlock process not working.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1022",
            source="zendesk",
            project_key="IT",
            summary="App crashes when opening messages",
            description="Mobile app crashes immediately when user opens the Messages tab. Other tabs work.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1023",
            source="zendesk",
            project_key="IT",
            summary="Search autocomplete not loading",
            description="Autocomplete suggestions never show. Likely related to throttled API endpoint.",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1024",
            source="zendesk",
            project_key="IT",
            summary="Exported PDF missing images",
            description="PDF exports do not include embedded images. Text renders fine.",
            status="open",
            priority="low",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1025",
            source="zendesk",
            project_key="IT",
            summary="Customer cannot change email address",
            description="Email change attempt returns validation error even for valid email formats.",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1026",
            source="zendesk",
            project_key="IT",
            summary="SAML login redirects in a loop",
            description="User stuck in login-redirection loop when using SAML SSO. Works in incognito mode.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1027",
            source="zendesk",
            project_key="IT",
            summary="User cannot see assigned tasks",
            description="Tasks page loads but shows blank list for this user only. Permissions appear correct.",
            status="open",
            priority="low",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1028",
            source="zendesk",
            project_key="IT",
            summary="Mobile app stuck on loading spinner",
            description="Customer reports mobile app remains on spinner forever after recent update.",
            status="in_progress",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1029",
            source="zendesk",
            project_key="IT",
            summary="Dark mode does not apply to all pages",
            description="Some pages revert to light mode despite user setting.",
            status="open",
            priority="low",
            created_at=now,
            updated_at=now,
        ),
        Ticket(
            external_key="INC-1030",
            source="zendesk",
            project_key="IT",
            summary="Email login hyperlink broken",
            description="Magic login link emailed to customer leads to 404 page.",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        ),
    ]

    for t in demo:
        session.add(t)
    session.commit()

    return MessageResponse(message="Demo tickets added")
