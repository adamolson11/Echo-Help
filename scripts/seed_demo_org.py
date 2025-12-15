from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlmodel import select
from sqlmodel import Session

from backend.app.db import SessionLocal, init_db
from backend.app.models.ticket import Ticket
from backend.app.models.ticket_feedback import TicketFeedback
from backend.app.models.snippets import SolutionSnippet, SnippetFeedback
from backend.app.services.embeddings import MODEL_NAME, embed_text
from backend.app.models.embedding import Embedding


def _now_utc() -> datetime:
    # Keep timezone-naive UTC for now to match existing codebase usage.
    return datetime.utcnow()


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
        t = Ticket(
            external_key=external_key,
            summary=summary,
            description=description,
            status=status,
            priority=priority,
            source=source,
            project_key=project_key,
            created_at=created_at,
        )
        session.add(t)
        session.commit()
        session.refresh(t)
        existing = t
    else:
        # keep idempotent but update content if we change the seed
        existing.summary = summary
        existing.description = description
        existing.status = status
        existing.priority = priority
        existing.source = source
        existing.project_key = project_key
        session.add(existing)
        session.commit()
    # Ensure body_md is present so KB/Ask Echo has consistent content
    if not getattr(existing, "body_md", None):
        existing.body_md = f"# {existing.summary}\n\n{existing.description}\n"
        session.add(existing)
        session.commit()
    return existing


def ensure_embedding(session: Session, ticket: Ticket) -> None:
    if ticket.id is None:
        return
    existing = session.exec(select(Embedding).where(Embedding.ticket_id == ticket.id)).first()
    if existing is not None:
        return
    text = f"{ticket.summary}\n\n{ticket.description or ''}".strip()
    try:
        vector = embed_text(text)
        emb = Embedding(ticket_id=ticket.id, text=text, vector=vector, model_name=MODEL_NAME)
        session.add(emb)
        session.commit()
    except Exception:
        # Demo seed should not block if embeddings are unavailable.
        session.rollback()


def ensure_ticket_feedback(
    session: Session,
    *,
    ticket_id: int,
    query_text: str,
    helped: bool | None,
    rating: int | None,
    resolution_notes: str | None,
    created_at: datetime,
) -> None:
    existing = session.exec(
        select(TicketFeedback).where(
            TicketFeedback.ticket_id == ticket_id,
            TicketFeedback.query_text == query_text,
            TicketFeedback.helped == helped,
        )
    ).first()
    if existing is not None:
        return
    fb = TicketFeedback(
        ticket_id=ticket_id,
        query_text=query_text,
        helped=helped,
        rating=rating,
        resolution_notes=resolution_notes,
        created_at=created_at,
    )
    session.add(fb)
    session.commit()


def ensure_snippet(
    session: Session,
    *,
    title: str,
    content_md: str,
    summary: str,
    source: str,
    echo_score: float,
    created_from_ticket_id: int | None = None,
) -> SolutionSnippet:
    existing = session.exec(select(SolutionSnippet).where(SolutionSnippet.title == title)).first()
    if existing is None:
        s = SolutionSnippet(
            title=title,
            content_md=content_md,
            summary=summary,
            source=source,
            echo_score=echo_score,
            ticket_id=created_from_ticket_id,
        )
        session.add(s)
        session.commit()
        session.refresh(s)
        return s

    existing.content_md = content_md
    existing.summary = summary
    existing.source = source
    existing.echo_score = echo_score
    if created_from_ticket_id is not None:
        existing.ticket_id = created_from_ticket_id
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing


def ensure_snippet_feedback(session: Session, *, snippet_id: int, helped: bool, created_at: datetime) -> None:
    existing = session.exec(
        select(SnippetFeedback).where(
            SnippetFeedback.snippet_id == snippet_id,
            SnippetFeedback.helped == helped,
        )
    ).first()
    if existing is not None:
        return
    sf = SnippetFeedback(snippet_id=snippet_id, helped=helped, created_at=created_at)
    session.add(sf)
    session.commit()


def seed_demo_org() -> None:
    init_db()

    now = _now_utc()
    rng = random.Random(1337)

    tickets_spec = [
        {
            "external_key": "DEMO-PR-001",
            "summary": "Password reset link loops back to login",
            "description": "User reports the password reset link opens, but after entering a new password the page redirects back to login without confirmation.",
            "status": "closed",
            "priority": "high",
            "project_key": "IT",
        },
        {
            "external_key": "DEMO-PR-002",
            "summary": "Password reset email not received",
            "description": "Reset email not arriving for specific domain users. Mail logs show DMARC alignment failures.",
            "status": "open",
            "priority": "medium",
            "project_key": "IT",
        },
        {
            "external_key": "DEMO-SSO-003",
            "summary": "SSO cookie causes reset flow to fail",
            "description": "SSO session persists across reset flow; user gets forced into old session. Clearing cookies/incognito resolves.",
            "status": "closed",
            "priority": "medium",
            "project_key": "IT",
        },
        {
            "external_key": "DEMO-AUTH-004",
            "summary": "Account locked after repeated MFA failures",
            "description": "Multiple MFA attempts triggered lockout. User cannot request reset until lockout cleared.",
            "status": "closed",
            "priority": "high",
            "project_key": "SEC",
        },
        {
            "external_key": "DEMO-NET-005",
            "summary": "VPN auth_failed when connecting",
            "description": "VPN client returns auth_failed. Cert bundle may be stale; rotating certs and re-auth works.",
            "status": "open",
            "priority": "high",
            "project_key": "NET",
        },
    ]

    # Expand with some "messy" tickets so search/semantic has more to chew on
    extras = []
    for i in range(6, 26):
        extras.append(
            {
                "external_key": f"DEMO-MISC-{i:03d}",
                "summary": rng.choice(
                    [
                        "Laptop fails to join Wi-Fi after sleep",
                        "Printer queue stuck in paused state",
                        "Build agent out of disk space",
                        "Intermittent 502 from internal service",
                        "Slack notifications delayed",
                        "Password reset shows expired token",
                    ]
                ),
                "description": rng.choice(
                    [
                        "Observed after OS update. Restarting network stack helps.",
                        "Clearing local spooler and re-adding printer resolves.",
                        "Deleted old artifacts; expanded volume.",
                        "Restarted ingress controller; checked upstream health.",
                        "Backlog cleared after reconnect; rate limits suspected.",
                        "Token TTL too short; user clock skew involved.",
                    ]
                ),
                "status": rng.choice(["open", "closed"]),
                "priority": rng.choice(["low", "medium", "high"]),
                "project_key": rng.choice(["IT", "OPS", "ENG"]),
            }
        )

    tickets_spec.extend(extras)

    with SessionLocal() as session:
        created: list[Ticket] = []
        for idx, spec in enumerate(tickets_spec):
            created_at = now - timedelta(days=30) + timedelta(days=idx % 14)
            t = ensure_ticket(
                session,
                external_key=spec["external_key"],
                summary=spec["summary"],
                description=spec["description"],
                status=spec["status"],
                priority=spec["priority"],
                source="demo_seed",
                project_key=spec["project_key"],
                created_at=created_at,
            )
            ensure_embedding(session, t)
            created.append(t)

        # Add some feedback events with resolution_notes so clustering/patterns have data
        pw_ticket = next(t for t in created if t.external_key == "DEMO-PR-001")
        if pw_ticket.id is not None:
            ensure_ticket_feedback(
                session,
                ticket_id=pw_ticket.id,
                query_text="Password reset doesn't work",
                helped=True,
                rating=4,
                resolution_notes="Cleared SSO cookies and re-issued reset link; user completed reset in incognito.",
                created_at=now - timedelta(days=2),
            )
            ensure_ticket_feedback(
                session,
                ticket_id=pw_ticket.id,
                query_text="Reset link loops back",
                helped=False,
                rating=2,
                resolution_notes="User was behind captive portal; reset page couldn't reach IdP reliably.",
                created_at=now - timedelta(days=1),
            )

        sso_ticket = next(t for t in created if t.external_key == "DEMO-SSO-003")
        if sso_ticket.id is not None:
            ensure_ticket_feedback(
                session,
                ticket_id=sso_ticket.id,
                query_text="Password reset loop",
                helped=True,
                rating=5,
                resolution_notes="Incognito window + cleared cookies fixed the reset loop.",
                created_at=now - timedelta(days=3),
            )

        # Seed a few snippets that are relevant to password reset
        s1 = ensure_snippet(
            session,
            title="Password reset loop (SSO cookies)",
            summary="If reset flow loops back to login, clear SSO cookies or use incognito.",
            content_md=(
                "## Symptoms\n"
                "- Reset link redirects to login repeatedly\n\n"
                "## Fix\n"
                "1. Clear SSO cookies for the IdP domain\n"
                "2. Retry in an incognito/private window\n"
                "3. Re-issue the reset link\n"
            ),
            source="demo_seed",
            echo_score=0.82,
            created_from_ticket_id=sso_ticket.id,
        )
        s2 = ensure_snippet(
            session,
            title="Password reset email missing (DMARC)",
            summary="If reset email isn't received, check DMARC/SPF alignment and mail logs.",
            content_md=(
                "## Symptoms\n"
                "- User never receives reset email\n"
                "- Mail logs show DMARC alignment failures\n\n"
                "## Fix\n"
                "- Verify SPF/DKIM for sending domain\n"
                "- Check DMARC policy and alignment\n"
                "- Confirm provider isn't quarantining\n"
            ),
            source="demo_seed",
            echo_score=0.74,
        )

        # Add snippet feedback so snippet radar has signal
        for helped, days_ago in [(True, 5), (True, 4), (False, 2)]:
            ensure_snippet_feedback(
                session,
                snippet_id=int(s1.id),
                helped=helped,
                created_at=now - timedelta(days=days_ago),
            )
        for helped, days_ago in [(True, 6), (False, 3), (False, 1)]:
            ensure_snippet_feedback(
                session,
                snippet_id=int(s2.id),
                helped=helped,
                created_at=now - timedelta(days=days_ago),
            )


def main() -> None:
    seed_demo_org()
    print("Seeded demo org data into echohelp.db")


if __name__ == "__main__":
    main()
