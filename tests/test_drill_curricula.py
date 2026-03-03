from __future__ import annotations

import json
from pathlib import Path

from backend.app.db import SessionLocal, init_db
from backend.app.models.ticket import Ticket
from backend.scripts.drill_ticket import load_curricula, list_curricula_text, select_ticket


def test_list_curricula_contains_known_pack(tmp_path: Path) -> None:
    path = tmp_path / "curricula.json"
    path.write_text(
        json.dumps(
            {
                "auth_week_1": {
                    "label": "Auth Week 1",
                    "filters": {"product_area": ["auth"], "severity": ["S2", "S3"], "status": ["Resolved", "Open"]},
                }
            }
        ),
        encoding="utf-8",
    )

    curricula = load_curricula(path)
    out = list_curricula_text(curricula)

    assert "auth_week_1" in out
    assert "Auth Week 1" in out


def test_curriculum_filters_ticket_selection() -> None:
    init_db()
    with SessionLocal() as session:
        session.add(
            Ticket(
                external_key="ECHO-CURR-1",
                source="seed",
                project_key="ECHO",
                summary="Auth callback issue",
                description="Auth issue",
                status="open",
                product_area="auth",
                severity="S2",
            )
        )
        session.add(
            Ticket(
                external_key="ECHO-CURR-2",
                source="seed",
                project_key="ECHO",
                summary="Billing issue",
                description="Billing issue",
                status="open",
                product_area="billing",
                severity="S2",
            )
        )
        session.commit()

    selected = select_ticket(
        status="any",
        area=None,
        env=None,
        severity=None,
        owning_team=None,
        key=None,
        curriculum_filters={"product_area": ["auth"], "severity": ["S2"], "status": ["Open"]},
    )

    assert selected.product_area == "auth"
    assert selected.severity == "S2"
