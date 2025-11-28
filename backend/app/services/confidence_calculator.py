from __future__ import annotations

from typing import Optional

from backend.app.models.snippets import SolutionSnippet


def calculate_echo_score(snippet: SolutionSnippet) -> float:
    """Simple Echo Score calculation.

    Returns a value between 0 and 1 based on success/failure counts and a
    small smoothing factor to avoid division by zero. This is intentionally
    lightweight for Phase 1 and can be replaced with a more sophisticated
    formula later.
    """
    sc = getattr(snippet, "success_count", 0) or 0
    fc = getattr(snippet, "failure_count", 0) or 0
    # Laplace smoothing
    score = (sc + 1) / (sc + fc + 2)
    # Ensure in [0,1]
    if score < 0:
        score = 0.0
    if score > 1:
        score = 1.0
    return float(score)
