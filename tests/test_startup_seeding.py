"""Verify that the app lifespan auto-seeds demo data on startup.

The conftest.py autouse fixture isolates each test to a fresh DB, so we can
assert that demo rows appear without any manual seed call — they must come from
the lifespan itself.
"""

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models.snippets import SolutionSnippet
from backend.app.models.ticket import Ticket


def test_lifespan_seeds_tickets_on_startup():
    """Starting the app should auto-insert at least the basic seed tickets."""
    with TestClient(app):
        with SessionLocal() as session:
            tickets = list(session.exec(select(Ticket)).all())
        assert len(tickets) >= 2, (
            f"Expected at least 2 seed tickets after startup, got {len(tickets)}"
        )


def test_lifespan_seeds_demo_org_on_startup():
    """Starting the app should auto-insert the full demo org data."""
    with TestClient(app):
        with SessionLocal() as session:
            demo_tickets = list(
                session.exec(select(Ticket).where(Ticket.source == "demo")).all()
            )
            demo_snippets = list(
                session.exec(
                    select(SolutionSnippet).where(SolutionSnippet.source == "demo")
                ).all()
            )

    assert len(demo_tickets) >= 10, (
        f"Expected >=10 demo tickets after startup, got {len(demo_tickets)}"
    )
    assert len(demo_snippets) >= 5, (
        f"Expected >=5 demo snippets after startup, got {len(demo_snippets)}"
    )


def test_lifespan_seeding_is_idempotent():
    """Starting the app twice must not double-insert demo rows."""
    with TestClient(app):
        pass  # first startup seeds the database

    with TestClient(app):
        with SessionLocal() as session:
            demo_tickets = list(
                session.exec(select(Ticket).where(Ticket.source == "demo")).all()
            )

    external_keys = [t.external_key for t in demo_tickets]
    assert len(external_keys) == len(set(external_keys)), (
        "Duplicate demo tickets found after two startup cycles — seeding is not idempotent"
    )
    assert len(demo_tickets) >= 10
