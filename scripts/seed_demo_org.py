from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from backend.app.db import SessionLocal, init_db
from backend.app.models.ask_echo_feedback import AskEchoFeedback
from backend.app.models.ask_echo_log import AskEchoLog
from backend.app.models.snippets import SnippetFeedback, SolutionSnippet
from backend.app.models.ticket import Ticket
from backend.app.models.ticket_feedback import TicketFeedback

DEMO_SOURCE = "demo"
DEMO_PREFIX = "DEMO"
DEMO_REASONING_NOTES = '{"demo": true}'


def _seed_base_time() -> datetime:
    return datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def ensure_ticket(
    session: Session,
    *,
    external_key: str,
    summary: str,
    description: str,
    status: str,
    priority: str,
    source: str,
    project_key: str,
    created_at: datetime,
) -> Ticket:
    existing = session.exec(select(Ticket).where(Ticket.external_key == external_key)).first()
    if existing is None:
        existing = Ticket(
            external_key=external_key,
            source=source,
            project_key=project_key,
            summary=summary,
            description=description,
            status=status,
            priority=priority,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(existing)
        session.commit()
        session.refresh(existing)
    else:
        existing.source = source
        existing.project_key = project_key
        existing.summary = summary
        existing.description = description
        existing.status = status
        existing.priority = priority
        existing.updated_at = created_at
        session.add(existing)
        session.commit()

    if not existing.body_md:
        existing.body_md = f"# {existing.summary}\n\n{existing.description}\n"
        session.add(existing)
        session.commit()
    return existing


def ensure_ticket_feedback(
    session: Session,
    *,
    ticket_id: int,
    query_text: str,
    helped: bool | None,
    rating: int,
    resolution_notes: str | None,
    created_at: datetime,
) -> TicketFeedback:
    existing = session.exec(
        select(TicketFeedback).where(
            TicketFeedback.ticket_id == ticket_id,
            TicketFeedback.query_text == query_text,
            TicketFeedback.rating == rating,
            TicketFeedback.helped == helped,
            TicketFeedback.ai_cluster_id == DEMO_SOURCE,
        )
    ).first()

    if existing is None:
        existing = TicketFeedback(
            ticket_id=ticket_id,
            query_text=query_text,
            rating=rating,
            helped=helped,
            resolution_notes=resolution_notes,
            ai_cluster_id=DEMO_SOURCE,
            created_at=created_at,
        )
        session.add(existing)
        session.commit()
        session.refresh(existing)
    else:
        existing.resolution_notes = resolution_notes
        existing.ai_cluster_id = DEMO_SOURCE
        existing.created_at = created_at
        session.add(existing)
        session.commit()

    return existing


def ensure_snippet(
    session: Session,
    *,
    title: str,
    summary: str,
    content_md: str,
    source: str,
    echo_score: float,
    ticket_id: int | None,
    created_at: datetime,
) -> SolutionSnippet:
    existing = session.exec(
        select(SolutionSnippet).where(
            SolutionSnippet.title == title,
            SolutionSnippet.source == source,
        )
    ).first()

    if existing is None:
        existing = SolutionSnippet(
            title=title,
            summary=summary,
            content_md=content_md,
            source=source,
            echo_score=echo_score,
            ticket_id=ticket_id,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(existing)
        session.commit()
        session.refresh(existing)
    else:
        existing.summary = summary
        existing.content_md = content_md
        existing.echo_score = echo_score
        existing.ticket_id = ticket_id
        existing.source = source
        existing.updated_at = created_at
        session.add(existing)
        session.commit()
    return existing


def ensure_snippet_feedback(
    session: Session,
    *,
    snippet_id: int,
    helped: bool,
    notes: str | None,
    created_at: datetime,
) -> SnippetFeedback:
    existing = session.exec(
        select(SnippetFeedback).where(
            SnippetFeedback.snippet_id == snippet_id,
            SnippetFeedback.helped == helped,
            SnippetFeedback.notes == notes,
        )
    ).first()

    if existing is None:
        existing = SnippetFeedback(
            snippet_id=snippet_id,
            helped=helped,
            notes=notes,
            created_at=created_at,
        )
        session.add(existing)
        session.commit()
        session.refresh(existing)
    else:
        existing.created_at = created_at
        session.add(existing)
        session.commit()
    return existing


def ensure_ask_echo_log(
    session: Session,
    *,
    query: str,
    mode: str,
    kb_confidence: float,
    echo_score: float,
    created_at: datetime,
) -> AskEchoLog:
    existing = session.exec(
        select(AskEchoLog).where(
            AskEchoLog.query == query,
            AskEchoLog.mode == mode,
            AskEchoLog.reasoning_notes == DEMO_REASONING_NOTES,
        )
    ).first()
    if existing is None:
        existing = AskEchoLog(
            query=query,
            mode=mode,
            kb_confidence=kb_confidence,
            echo_score=echo_score,
            reasoning_notes=DEMO_REASONING_NOTES,
            created_at=created_at,
        )
        session.add(existing)
        session.commit()
        session.refresh(existing)
    else:
        existing.kb_confidence = kb_confidence
        existing.echo_score = echo_score
        existing.created_at = created_at
        session.add(existing)
        session.commit()
    return existing


def ensure_ask_echo_feedback(
    session: Session,
    *,
    ask_echo_log_id: int,
    helped: bool,
    notes: str | None,
    created_at: datetime,
) -> AskEchoFeedback:
    existing = session.exec(
        select(AskEchoFeedback).where(
            AskEchoFeedback.ask_echo_log_id == ask_echo_log_id,
            AskEchoFeedback.helped == helped,
            AskEchoFeedback.notes == notes,
        )
    ).first()
    if existing is None:
        existing = AskEchoFeedback(
            ask_echo_log_id=ask_echo_log_id,
            helped=helped,
            notes=notes,
            created_at=created_at,
        )
        session.add(existing)
        session.commit()
        session.refresh(existing)
    else:
        existing.created_at = created_at
        session.add(existing)
        session.commit()
    return existing


def seed_demo_org() -> None:
    init_db()
    base = _seed_base_time()

    tickets_spec = [
        # password reset
        {
            "external_key": "DEMO-PWRESET-001",
            "summary": "Password reset doesn't work (login loop)",
            "description": "Customer says: password reset doesn't work. After setting a new password, user is redirected back to login without confirmation.",
            "status": "open",
            "priority": "high",
            "project_key": "IT",
        },
        {
            "external_key": "DEMO-PWRESET-002",
            "summary": "Password reset email not received",
            "description": "Reset email missing for a subset of users. DMARC alignment failures for the sender domain.",
            "status": "open",
            "priority": "medium",
            "project_key": "IT",
        },
        # MFA
        {
            "external_key": "DEMO-MFA-001",
            "summary": "MFA code not delivered",
            "description": "SMS MFA codes are delayed or never arrive. Email verification works.",
            "status": "open",
            "priority": "high",
            "project_key": "SEC",
        },
        {
            "external_key": "DEMO-MFA-002",
            "summary": "Authenticator codes rejected due to clock drift",
            "description": "Authenticator app produces invalid codes; device time is off by ~90 seconds.",
            "status": "closed",
            "priority": "medium",
            "project_key": "SEC",
        },
        # VPN
        {
            "external_key": "DEMO-VPN-001",
            "summary": "VPN auth_failed when connecting",
            "description": "VPN client returns auth_failed. Rotating cert bundle and re-auth resolves.",
            "status": "open",
            "priority": "high",
            "project_key": "NET",
        },
        {
            "external_key": "DEMO-VPN-002",
            "summary": "VPN disconnects every few minutes",
            "description": "Intermittent VPN disconnects, especially when switching networks.",
            "status": "open",
            "priority": "medium",
            "project_key": "NET",
        },
        # printer
        {
            "external_key": "DEMO-PRINTER-001",
            "summary": "Printer queue stuck paused",
            "description": "Queue stuck in paused state; spooler restart temporarily helps.",
            "status": "open",
            "priority": "low",
            "project_key": "IT",
        },
        {
            "external_key": "DEMO-PRINTER-002",
            "summary": "Printer prints blank pages",
            "description": "Print job completes but pages are blank; driver mismatch suspected.",
            "status": "closed",
            "priority": "low",
            "project_key": "IT",
        },
        # SSO cookie loop
        {
            "external_key": "DEMO-SSO-001",
            "summary": "SSO cookie loop blocks login",
            "description": "SSO session persists across auth redirect; clearing cookies/incognito resolves.",
            "status": "closed",
            "priority": "medium",
            "project_key": "IT",
        },
        # lockout
        {
            "external_key": "DEMO-LOCKOUT-001",
            "summary": "Account locked after repeated MFA failures",
            "description": "Multiple MFA attempts triggered lockout; user cannot authenticate until lockout cleared.",
            "status": "closed",
            "priority": "high",
            "project_key": "SEC",
        },
        # bad / incomplete
        {
            "external_key": "DEMO-BAD-001",
            "summary": "Login broken",
            "description": "",
            "status": "open",
            "priority": "medium",
            "project_key": "IT",
        },
        {
            "external_key": "DEMO-BAD-002",
            "summary": "Something is wrong with SSO",
            "description": "User reports issues but no repro steps provided.",
            "status": "open",
            "priority": "low",
            "project_key": "IT",
        },
    ]

    with SessionLocal() as session:
        created: list[Ticket] = []
        for idx, spec in enumerate(tickets_spec):
            created.append(
                ensure_ticket(
                    session,
                    external_key=spec["external_key"],
                    summary=spec["summary"],
                    description=spec["description"],
                    status=spec["status"],
                    priority=spec["priority"],
                    source=DEMO_SOURCE,
                    project_key=spec["project_key"],
                    created_at=base + timedelta(hours=idx),
                )
            )

        by_key = {t.external_key: t for t in created}

        def tid(key: str) -> int:
            ticket = by_key[key]
            assert ticket.id is not None
            return int(ticket.id)

        # 3+ resolvable via resolution_notes
        fb_base = base + timedelta(days=1)
        ensure_ticket_feedback(
            session,
            ticket_id=tid("DEMO-PWRESET-001"),
            query_text="password reset doesn't work",
            helped=True,
            rating=5,
            resolution_notes="Clear SSO cookies / incognito; invalidate sessions; retry reset flow. Confirm user clock is correct.",
            created_at=fb_base,
        )
        ensure_ticket_feedback(
            session,
            ticket_id=tid("DEMO-VPN-001"),
            query_text="vpn auth_failed",
            helped=True,
            rating=4,
            resolution_notes="Rotate VPN cert bundle, re-enroll device, and re-authenticate.",
            created_at=fb_base + timedelta(hours=1),
        )
        ensure_ticket_feedback(
            session,
            ticket_id=tid("DEMO-MFA-002"),
            query_text="mfa codes invalid",
            helped=True,
            rating=4,
            resolution_notes="Sync device clock (enable automatic time) and retry MFA.",
            created_at=fb_base + timedelta(hours=2),
        )

        snip_base = base + timedelta(days=2)
        s1 = ensure_snippet(
            session,
            title="password reset doesn't work — fix login loop",
            summary="password reset doesn't work — clear cookies and invalidate sessions",
            content_md=(
                "### Fix: password reset doesn't work (login loop)\n\n"
                "1) Clear SSO cookies (or use incognito)\n"
                "2) Invalidate existing sessions\n"
                "3) Retry password reset\n\n"
                "If token still fails: check user clock and token TTL.\n"
            ),
            source=DEMO_SOURCE,
            echo_score=0.9,
            ticket_id=tid("DEMO-PWRESET-001"),
            created_at=snip_base,
        )
        s2 = ensure_snippet(
            session,
            title="VPN auth_failed — rotate cert bundle",
            summary="vpn auth_failed — rotate cert bundle",
            content_md=(
                "### Fix: VPN auth_failed\n\n"
                "- Rotate cert bundle\n"
                "- Re-enroll device\n"
                "- Re-authenticate\n"
            ),
            source=DEMO_SOURCE,
            echo_score=0.8,
            ticket_id=tid("DEMO-VPN-001"),
            created_at=snip_base + timedelta(hours=1),
        )
        s3 = ensure_snippet(
            session,
            title="MFA codes invalid — fix clock drift",
            summary="mfa codes invalid — fix clock drift",
            content_md="### Fix: MFA codes invalid\n\nEnable automatic time sync on the device; retry MFA.\n",
            source=DEMO_SOURCE,
            echo_score=0.75,
            ticket_id=tid("DEMO-MFA-002"),
            created_at=snip_base + timedelta(hours=2),
        )
        s4 = ensure_snippet(
            session,
            title="SSO cookie loop — clear cookies",
            summary="sso cookie loop — clear cookies",
            content_md="### Fix: SSO cookie loop\n\nClear cookies for the IdP/app domain; try incognito.\n",
            source=DEMO_SOURCE,
            echo_score=0.7,
            ticket_id=tid("DEMO-SSO-001"),
            created_at=snip_base + timedelta(hours=3),
        )
        s5 = ensure_snippet(
            session,
            title="Printer queue paused — restart spooler",
            summary="printer queue paused — restart spooler",
            content_md="### Fix: printer queue paused\n\nRestart spooler and re-add printer if needed.\n",
            source=DEMO_SOURCE,
            echo_score=0.6,
            ticket_id=tid("DEMO-PRINTER-001"),
            created_at=snip_base + timedelta(hours=4),
        )

        for i, snippet in enumerate([s1, s2, s3, s4, s5]):
            assert snippet.id is not None
            ensure_snippet_feedback(
                session,
                snippet_id=int(snippet.id),
                helped=True,
                notes=f"{DEMO_PREFIX}: helpful",
                created_at=snip_base + timedelta(days=1, hours=i),
            )

        log = ensure_ask_echo_log(
            session,
            query="password reset doesn't work",
            mode="kb_answer",
            kb_confidence=0.9,
            echo_score=0.9,
            created_at=base + timedelta(days=3),
        )
        if log.id is not None:
            ensure_ask_echo_feedback(
                session,
                ask_echo_log_id=int(log.id),
                helped=True,
                notes=f"{DEMO_PREFIX}: worked",
                created_at=base + timedelta(days=3, hours=1),
            )


def main() -> None:
    seed_demo_org()
    print("Seeded demo org data into echohelp.db")


if __name__ == "__main__":
    main()
