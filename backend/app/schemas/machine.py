from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .meta import Meta


class MachineStatusResponse(BaseModel):
    meta: Meta = Meta(kind="machine_status", version="v1")

    tickets_total: int
    snippets_total: int
    ask_echo_total: int

    ask_echo_ungrounded_rate_30d: float
    feedback_total_30d: int

    last_event_at: datetime | None = None
