from __future__ import annotations


def clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def calculate_kb_confidence(
    *,
    kb_backed: bool,
    top_snippet_echo_score: float | None,
    top_ticket_score: float,
    has_snippets: bool,
    has_tickets: bool,
) -> float:
    """Return an explicit, stable KB confidence in [0,1].

    Philosophy (v1):
    - If we are not KB-backed, confidence is 0.
    - If we have snippet evidence, snippet echo_score is the primary signal.
    - Otherwise, rely on top ticket score.

    This is intentionally simple and deterministic; future versions can blend
    more signals but should remain explicit and test-guarded.
    """
    if not kb_backed:
        return 0.0

    if has_snippets and top_snippet_echo_score is not None:
        return clamp01(float(top_snippet_echo_score))

    if has_tickets:
        return clamp01(float(top_ticket_score or 0.0))

    # KB-backed with no evidence should not happen, but be safe.
    return 0.0
