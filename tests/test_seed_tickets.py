from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import select

from backend.app.db import SessionLocal
from backend.app.models.ticket import Ticket
from backend.scripts.generate_seed_tickets import generate_rows
from backend.scripts.seed_tickets import seed_tickets


def test_seed_tickets_idempotent_reset(tmp_path: Path) -> None:
    rows = generate_rows(count=50, seed=123)
    seed_path = tmp_path / "tickets_big_seed.jsonl"
    seed_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    dry = seed_tickets(path=seed_path, reset=False, source="seed_test", dry_run=True)
    first = seed_tickets(path=seed_path, reset=True, source="seed_test")
    second = seed_tickets(path=seed_path, reset=False, source="seed_test")

    assert dry == 50
    assert first == 50
    assert second == 50

    with SessionLocal() as session:
        rows = list(session.exec(select(Ticket).where(Ticket.source == "seed_test")).all())
        assert len(rows) == 50
        first_row = rows[0]
        assert first_row.external_key and first_row.external_key.startswith("ECHO-")
        assert first_row.summary
        assert first_row.description
        assert first_row.product_area in {"auth", "billing", "search", "embeddings", "frontend", "integrations"}
        assert first_row.environment in {"local", "stage", "prod"}
        assert first_row.severity in {"S1", "S2", "S3", "S4"}
        assert first_row.priority in {"P0", "P1", "P2", "P3"}
        assert first_row.answer_quality_label in {"good", "bad", "mixed"}
        assert first_row.source_system == "seed"
        assert first_row.owning_team
        assert first_row.escalation_target
