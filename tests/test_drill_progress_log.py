from __future__ import annotations

import json
from pathlib import Path

from backend.scripts.drill_ticket import build_session_row, log_session_row, session_summary


def test_progress_log_row_and_summary(tmp_path: Path) -> None:
    out = tmp_path / "drill_sessions.jsonl"

    row1 = build_session_row(
        curriculum="auth_week_1",
        ticket_key="ECHO-101",
        mode="evaluate",
        score=70,
        missed=["env"],
        user_answer_path="/tmp/a1.txt",
    )
    row2 = build_session_row(
        curriculum="auth_week_1",
        ticket_key="ECHO-102",
        mode="evaluate",
        score=90,
        missed=["verification"],
        user_answer_path="/tmp/a2.txt",
    )

    log_session_row(out, row1)
    log_session_row(out, row2)

    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    parsed = json.loads(lines[0])
    assert set(["ts", "curriculum", "ticket_key", "mode", "score", "missed", "user_answer_path"]).issubset(parsed.keys())

    summary = session_summary(out, curriculum="auth_week_1")
    assert int(summary["attempts"]) == 2
    assert float(summary["avg_score"]) == 80.0
    assert float(summary["last_5_avg_score"]) == 80.0
