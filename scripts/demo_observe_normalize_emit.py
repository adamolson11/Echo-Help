"""Run the existing observe -> normalize -> emit prototype loop on one sample thread."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.ingest import IngestThread
from backend.app.services.findings import emit_ticket_draft, normalize_ingest_thread

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = REPO_ROOT / "sample_data" / "sample_thread_slack.json"


def main() -> int:
    payload = json.loads(SAMPLE_PATH.read_text())
    thread = IngestThread.model_validate(payload)
    finding = normalize_ingest_thread(thread)
    artifact = emit_ticket_draft(finding)

    print("Normalized finding:")
    print(finding.model_dump_json(indent=2))
    print()
    print("Emitted artifact:")
    print(artifact.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
