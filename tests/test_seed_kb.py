from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.app.main import app
from backend.app.db import SessionLocal
from backend.app.models.kb_entry import KBEntry
from backend.app.models.ticket import Ticket
from backend.scripts.seed_kb import seed_kb


def _kb_rows() -> list[dict]:
    return [
        {
            "id": "KB-T-1",
            "title": "How to set up auth callback",
            "body_markdown": "Steps to configure auth callback and verify redirect.",
            "tags": ["auth", "setup", "how to"],
            "product_area": "auth",
            "updated_at": "2026-02-01T10:00:00+00:00",
            "source_system": "seed_kb",
        },
        {
            "id": "KB-T-2",
            "title": "Search ranking regression checklist",
            "body_markdown": "Run hit@3 baseline comparison before deploy.",
            "tags": ["search", "checklist"],
            "product_area": "search",
            "updated_at": "2026-02-02T10:00:00+00:00",
            "source_system": "seed_kb",
        },
    ]


def test_seed_kb_inserts_expected_count(tmp_path: Path) -> None:
    path = tmp_path / "kb_seed.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in _kb_rows()) + "\n", encoding="utf-8")

    dry = seed_kb(path=path, dry_run=True, reset=False)
    inserted = seed_kb(path=path, reset=True)

    assert dry == 2
    assert inserted == 2
    with SessionLocal() as session:
        rows = list(session.exec(select(KBEntry)).all())
        assert len(rows) == 2


def test_ask_echo_includes_kb_evidence_when_available() -> None:
    with SessionLocal() as session:
        now = datetime.now(UTC)
        session.add(
            KBEntry(
                entry_id="KB-Q-1",
                title="How do I set up auth callback safely",
                body_markdown="Steps and setup checks for callback configuration.",
                tags=["auth", "how do i", "setup"],
                product_area="auth",
                source_system="seed_kb",
                updated_at=now,
            )
        )
        session.add(
            Ticket(
                external_key="ECHO-KB-1",
                source="seed",
                project_key="ECHO",
                summary="Auth callback setup issue",
                description="Need setup steps for callback config",
                status="open",
                product_area="auth",
                environment="prod",
                priority="P1",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    client = TestClient(app)
    resp = client.post("/api/ask-echo", json={"q": "how do I setup auth callback", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("kb_evidence"), list)
    assert len(data["kb_evidence"]) >= 1
    assert data["kb_evidence"][0].get("entry_id")
