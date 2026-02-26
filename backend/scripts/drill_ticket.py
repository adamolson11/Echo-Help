from __future__ import annotations

import argparse
import random
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


def select_ticket(
    *,
    status: str,
    area: str | None,
    env: str | None,
    severity: str | None,
    owning_team: str | None,
    key: str | None,
) -> Ticket:
    init_db()
    with SessionLocal() as session:
        rows = list(session.exec(select(Ticket)).all())

    filtered: list[Ticket] = []
    for row in rows:
        if key and (row.external_key != key and row.key != key and row.short_id != key):
            continue
        if area and (row.product_area or "").lower() != area.lower():
            continue
        if env and (row.environment or "").lower() != env.lower():
            continue
        if severity and (row.severity or "").upper() != severity.upper():
            continue
        if status == "open" and _is_resolved(row):
            continue
        if status == "resolved" and not _is_resolved(row):
            continue
        team, _ = TEAM_MAP.get((row.product_area or "").lower(), ("general-support", "oncall-support"))
        if owning_team and team != owning_team:
            continue
        filtered.append(row)

    if not filtered:
        raise ValueError("No ticket matched provided filters")
    return random.choice(filtered)


def render_drill(ticket: Ticket, *, mode: str, comments_limit: int = 4, answer_text: str | None = None) -> str:
    area = (ticket.product_area or "").lower()
    team, escalation = TEAM_MAP.get(area, ("general-support", "oncall-support"))
    resolved = _is_resolved(ticket)

    lines: list[str] = []
    lines.append("TRIAGE BLOCK")
    lines.append(f"- Summary: {ticket.summary}")
    lines.append(f"- Environment: {ticket.environment or 'unknown'}")
    lines.append(f"- Severity/Priority: {ticket.severity or 'unknown'} / {ticket.priority or 'unknown'}")
    for bullet in _what_to_ask(ticket):
        lines.append(f"- Ask next: {bullet}")
    lines.append(f"- Escalation target suggestion: {team} -> {escalation}")

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
    parser.add_argument("--mode", choices=["prompt", "reveal", "evaluate"], default="prompt")
    parser.add_argument("--comments", type=int, default=4)
    parser.add_argument("--answer-file", type=Path, default=None)
    args = parser.parse_args()

    ticket = select_ticket(
        status=args.status,
        area=args.area,
        env=args.env,
        severity=args.severity,
        owning_team=args.owning_team,
        key=args.key,
    )
    answer_text = args.answer_file.read_text(encoding="utf-8") if args.answer_file and args.answer_file.exists() else None
    print(render_drill(ticket, mode=args.mode, comments_limit=args.comments, answer_text=answer_text))


if __name__ == "__main__":
    main()
