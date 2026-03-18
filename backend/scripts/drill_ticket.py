from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import select

from backend.app.db import SessionLocal, init_db
from backend.app.models.ticket import Ticket


TEAM_MAP = {
    "auth": ("identity-platform", "oncall-identity"),
    "billing": ("billing-core", "oncall-billing"),
    "search": ("search-relevance", "oncall-search"),
    "embeddings": ("ml-platform", "oncall-ml"),
    "frontend": ("web-experience", "oncall-web"),
    "integrations": ("integrations-core", "oncall-integrations"),
}

DEFAULT_CURRICULA_PATH = Path("backend/app/seed_data/curricula.json")
DEFAULT_SESSION_OUT = Path("backend/app/seed_data/drill_sessions.jsonl")


def _is_resolved(ticket: Ticket) -> bool:
    status = (ticket.status or "").strip().lower()
    return status in {"resolved", "closed", "done"} or ticket.resolved_at is not None


def _what_to_ask(ticket: Ticket) -> list[str]:
    env = (ticket.environment or "unknown").lower()
    return [
        f"Confirm exact environment and tenant where issue appears (currently: {env}).",
        "Request timestamp, request id, and relevant logs/screenshots from the failing attempt.",
        "Ask for exact repro sequence and whether issue is new, intermittent, or after a recent change.",
    ]


def _thread_preview(ticket: Ticket, include_resolution: bool, comments_limit: int) -> list[dict]:
    items: list[dict] = []
    items.append({"type": "REPORT", "text": (ticket.description or "").strip()})
    for bad in (ticket.resolution_bad or []):
        items.append(
            {
                "type": "DID_NOT_WORK",
                "text": str(bad),
                "why_wrong": (ticket.bad_reason or "") if ticket.bad_reason else None,
            }
        )

    if include_resolution:
        for good in (ticket.resolution_good or []):
            items.append({"type": "FINAL_FIX", "text": str(good)})

    return items[: max(1, comments_limit)]


def _evaluate_answer(ticket: Ticket, answer_text: str) -> tuple[int, list[str]]:
    text = (answer_text or "").lower()
    score = 100
    missed: list[str] = []
    if ticket.environment and ticket.environment.lower() not in text:
        score -= 25
        missed.append("Did not reference environment context.")
    if not any(tok in text for tok in ("log", "request id", "trace", "repro")):
        score -= 30
        missed.append("Did not request logs/request-id/repro details.")
    if any(tok in text for tok in ("drop", "delete", "wipe", "truncate")):
        score -= 30
        missed.append("Suggested potentially destructive action.")
    if "rollback" not in text and "verify" not in text:
        score -= 15
        missed.append("Missing verification/rollback safety mention.")
    return max(0, score), missed


def load_curricula(path: Path = DEFAULT_CURRICULA_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict] = {}
    for name, cfg in data.items():
        if isinstance(name, str) and isinstance(cfg, dict):
            out[name] = cfg
    return out


def list_curricula_text(curricula: dict[str, dict]) -> str:
    if not curricula:
        return "No curricula configured."
    lines = ["Available curricula:"]
    for name in sorted(curricula.keys()):
        row = curricula[name]
        label = str(row.get("label") or name)
        desc = str(row.get("description") or "")
        lines.append(f"- {name}: {label}" + (f" — {desc}" if desc else ""))
    return "\n".join(lines)


def _norm_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def build_session_row(
    *,
    curriculum: str | None,
    ticket_key: str,
    mode: str,
    score: int | None,
    missed: list[str],
    user_answer_path: str | None,
) -> dict:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "curriculum": curriculum,
        "ticket_key": ticket_key,
        "mode": mode,
        "score": score,
        "missed": missed,
        "user_answer_path": user_answer_path,
    }


def log_session_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def session_summary(path: Path, *, curriculum: str | None = None) -> dict[str, float | int]:
    if not path.exists():
        return {"attempts": 0, "avg_score": 0.0, "last_5_avg_score": 0.0}

    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if curriculum and row.get("curriculum") != curriculum:
                continue
            rows.append(row)

    scores = [int(r["score"]) for r in rows if isinstance(r.get("score"), int)]
    if not scores:
        return {"attempts": len(rows), "avg_score": 0.0, "last_5_avg_score": 0.0}

    avg = sum(scores) / float(len(scores))
    last = scores[-5:]
    last_avg = sum(last) / float(len(last))
    return {"attempts": len(rows), "avg_score": avg, "last_5_avg_score": last_avg}


def select_ticket(
    *,
    status: str,
    area: str | None,
    env: str | None,
    severity: str | None,
    owning_team: str | None,
    key: str | None,
    curriculum_filters: dict | None = None,
) -> Ticket:
    init_db()
    with SessionLocal() as session:
        rows = list(session.exec(select(Ticket)).all())

    curriculum_filters = curriculum_filters or {}
    c_area = [x.lower() for x in _norm_list(curriculum_filters.get("product_area"))]
    c_env = [x.lower() for x in _norm_list(curriculum_filters.get("environment"))]
    c_severity = [x.upper() for x in _norm_list(curriculum_filters.get("severity"))]
    c_status = [x.lower() for x in _norm_list(curriculum_filters.get("status"))]
    c_team = [x for x in _norm_list(curriculum_filters.get("owning_team"))]

    filtered: list[Ticket] = []
    for row in rows:
        if key and (row.external_key != key and row.key != key and row.short_id != key):
            continue
        row_area = (row.product_area or "").lower()
        row_env = (row.environment or "").lower()
        row_sev = (row.severity or "").upper()

        if area:
            if row_area != area.lower():
                continue
        elif c_area and row_area not in c_area:
            continue

        if env:
            if row_env != env.lower():
                continue
        elif c_env and row_env not in c_env:
            continue

        if severity:
            if row_sev != severity.upper():
                continue
        elif c_severity and row_sev not in c_severity:
            continue

        resolved = _is_resolved(row)
        if status == "open" and resolved:
            continue
        if status == "resolved" and not resolved:
            continue
        if status == "any" and c_status:
            allowed_open = "open" in c_status
            allowed_resolved = "resolved" in c_status or "closed" in c_status
            if resolved and not allowed_resolved:
                continue
            if (not resolved) and not allowed_open:
                continue

        team = (row.owning_team or "").strip()
        if not team:
            team, _ = TEAM_MAP.get((row.product_area or "").lower(), ("general-support", "oncall-support"))
        if owning_team:
            if team != owning_team:
                continue
        elif c_team and team not in c_team:
            continue
        filtered.append(row)

    if not filtered:
        raise ValueError("No ticket matched provided filters")
    return random.choice(filtered)


def render_drill(ticket: Ticket, *, mode: str, comments_limit: int = 4, answer_text: str | None = None) -> str:
    area = (ticket.product_area or "").lower()
    explicit_team = (ticket.owning_team or "").strip()
    explicit_escalation = (ticket.escalation_target or "").strip()
    fallback_team, fallback_escalation = TEAM_MAP.get(area, ("general-support", "oncall-support"))
    team = explicit_team or fallback_team or "Unknown"
    escalation = explicit_escalation or fallback_escalation or "Unknown"
    resolved = _is_resolved(ticket)

    lines: list[str] = []
    lines.append("TRIAGE BLOCK")
    lines.append(f"- Summary: {ticket.summary}")
    lines.append(f"- Environment: {ticket.environment or 'unknown'}")
    lines.append(f"- Severity/Priority: {ticket.severity or 'unknown'} / {ticket.priority or 'unknown'}")
    lines.append(f"- Owning Team: {team}")
    lines.append(f"- Escalation Target: {escalation}")
    for bullet in _what_to_ask(ticket):
        lines.append(f"- Ask next: {bullet}")

    lines.append("")
    lines.append("QA BLOCK")
    if ticket.repro_steps:
        lines.append("- Repro steps:")
        for step in ticket.repro_steps:
            lines.append(f"  - {step}")
    else:
        lines.append("- Repro steps missing: request customer-provided exact steps.")
    lines.append(f"- Expected: {ticket.expected_result or 'not provided'}")
    lines.append(f"- Actual: {ticket.actual_result or 'not provided'}")
    lines.append("- Minimal test plan template:")
    lines.append("  - confirm repro")
    lines.append("  - isolate variable")
    lines.append("  - regression checks")
    lines.append("  - verification steps once fixed")

    lines.append("")
    lines.append("THREAD PREVIEW")
    thread = _thread_preview(ticket, include_resolution=(mode == "reveal"), comments_limit=comments_limit)
    for item in thread:
        line = f"- [{item['type']}] {item.get('text', '')}".strip()
        if item.get("why_wrong"):
            line += f" | why_wrong: {item['why_wrong']}"
        lines.append(line)

    if mode == "reveal":
        lines.append("")
        lines.append("REVEAL")
        lines.append(f"- Final fix: {(ticket.resolution_good or ['not recorded'])[0]}")
        lines.append(f"- Root cause: {ticket.root_cause_good or ticket.root_cause or 'not recorded'}")
        lines.append(f"- Verification steps: {'; '.join(ticket.resolution_good or ['verify with customer and monitor logs'])}")

    if mode == "evaluate":
        score, missed = _evaluate_answer(ticket, answer_text or "")
        lines.append("")
        lines.append("EVALUATION")
        lines.append(f"- Score: {score}/100")
        if missed:
            lines.append("- Missed items:")
            for m in missed:
                lines.append(f"  - {m}")
        else:
            lines.append("- Missed items: none")

    if mode == "prompt" and resolved:
        lines.append("")
        lines.append("(Resolution intentionally hidden in prompt mode)")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Training Simulator: Ticket Drill Mode")
    parser.add_argument("--status", choices=["open", "resolved", "any"], default="any")
    parser.add_argument("--area", type=str, default=None)
    parser.add_argument("--env", type=str, default=None)
    parser.add_argument("--severity", type=str, default=None)
    parser.add_argument("--owning-team", type=str, default=None)
    parser.add_argument("--key", type=str, default=None)
    parser.add_argument("--curriculum", type=str, default=None)
    parser.add_argument("--curricula-path", type=Path, default=DEFAULT_CURRICULA_PATH)
    parser.add_argument("--list-curricula", action="store_true")
    parser.add_argument("--mode", choices=["prompt", "reveal", "evaluate"], default="prompt")
    parser.add_argument("--comments", type=int, default=4)
    parser.add_argument("--answer-file", type=Path, default=None)
    parser.add_argument("--log-session", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--session-out", type=Path, default=DEFAULT_SESSION_OUT)
    args = parser.parse_args()

    curricula = load_curricula(args.curricula_path)
    if args.list_curricula:
        print(list_curricula_text(curricula))
        return

    curriculum_filters: dict | None = None
    if args.curriculum:
        row = curricula.get(args.curriculum)
        if row is None:
            raise ValueError(f"Unknown curriculum: {args.curriculum}")
        curriculum_filters = row.get("filters") if isinstance(row.get("filters"), dict) else {}

    ticket = select_ticket(
        status=args.status,
        area=args.area,
        env=args.env,
        severity=args.severity,
        owning_team=args.owning_team,
        key=args.key,
        curriculum_filters=curriculum_filters,
    )
    answer_text = args.answer_file.read_text(encoding="utf-8") if args.answer_file and args.answer_file.exists() else None
    print(render_drill(ticket, mode=args.mode, comments_limit=args.comments, answer_text=answer_text))

    score: int | None = None
    missed: list[str] = []
    if args.mode == "evaluate":
        score, missed = _evaluate_answer(ticket, answer_text or "")

    if args.log_session:
        ticket_key = ticket.external_key or ticket.key or ticket.short_id or "unknown"
        row = build_session_row(
            curriculum=args.curriculum,
            ticket_key=ticket_key,
            mode=args.mode,
            score=score,
            missed=missed,
            user_answer_path=str(args.answer_file) if args.answer_file else None,
        )
        log_session_row(args.session_out, row)
        summary = session_summary(args.session_out, curriculum=args.curriculum)
        print("\nSESSION SUMMARY")
        print(f"- attempts: {int(summary['attempts'])}")
        print(f"- avg_score: {float(summary['avg_score']):.2f}")
        print(f"- last_5_avg_score: {float(summary['last_5_avg_score']):.2f}")


if __name__ == "__main__":
    main()
