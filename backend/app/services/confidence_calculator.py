from __future__ import annotations

from typing import Optional
from datetime import datetime, timezone

from backend.app.models.snippets import SolutionSnippet


def calculate_echo_score(snippet: SolutionSnippet) -> float:
    """Improved Echo Score that combines a smoothed success ratio,
    recency, and volume signals.

    Weighted components:
    - base_ratio (70%): Laplace-smoothed success rate
    - recency_boost (20%): more recent snippets get a small boost
    - volume_boost (10%): more trials increase confidence
    """
    sc = getattr(snippet, "success_count", 0) or 0
    fc = getattr(snippet, "failure_count", 0) or 0
    total = sc + fc

    # Base Laplace-smoothed success ratio
    base_ratio = (sc + 1) / (total + 2) if total >= 0 else 0.5

    # Recency: use `updated_at` if available, otherwise `created_at`.
    recency_boost = 0.0
    ts = getattr(snippet, "updated_at", None) or getattr(snippet, "created_at", None)
    if ts:
        try:
            now = datetime.now(timezone.utc)
            # Ensure ts is timezone-aware if possible; fallback to naive
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_days = (now - ts).total_seconds() / 86400.0
            # recent within 0-30 days gives a linearly decaying boost 1.0->0.0
            recency_boost = max(0.0, 1.0 - min(age_days / 30.0, 1.0))
        except Exception:
            recency_boost = 0.0

    # Volume boost: more data increases confidence (caps at 1.0)
    volume_boost = min(total / 10.0, 1.0)

    score = base_ratio * 0.7 + recency_boost * 0.2 + volume_boost * 0.1
    # clamp and round
    score = max(0.0, min(1.0, score))
    return float(round(score, 4))
