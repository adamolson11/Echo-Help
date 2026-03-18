from backend.app.services.ranking_policy import calculate_kb_confidence


def test_calculate_kb_confidence_uses_multiple_signals_and_stays_bounded() -> None:
    confidence = calculate_kb_confidence(
        kb_backed=True,
        top_snippet_echo_score=1.6,
        top_ticket_score=1.2,
        has_snippets=True,
        has_tickets=True,
        semantic_similarity=0.9,
        keyword_overlap=0.8,
        recency=0.7,
    )

    assert 0.0 <= confidence <= 1.0
    assert confidence > 0.9


def test_calculate_kb_confidence_fallback_is_zero_when_not_grounded() -> None:
    confidence = calculate_kb_confidence(
        kb_backed=False,
        top_snippet_echo_score=0.9,
        top_ticket_score=0.8,
        has_snippets=True,
        has_tickets=True,
        semantic_similarity=0.9,
        keyword_overlap=0.8,
        recency=0.7,
    )

    assert confidence == 0.0
