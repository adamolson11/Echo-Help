from backend.app.services.feedback import build_feedback_analytics


def test_build_feedback_analytics_marks_low_confidence_no_source_fallback() -> None:
    analytics = build_feedback_analytics(
        answer="  Fallback answer only  ",
        confidence=0.0,
        sources=[],
        reasoning="Fallback answer because no strong KB-backed match was available.",
        mode="general_answer",
    )

    assert analytics["answer_text"] == "Fallback answer only"
    assert analytics["source_count"] == 0
    assert analytics["low_confidence"] is True
    assert analytics["no_sources"] is True
    assert analytics["fallback_only"] is True
    assert analytics["feedback_status"] == "pending"
    assert analytics["feedback_rating"] == 0
    assert "Fallback-only answer" in analytics["reasoning_summary"]


def test_build_feedback_analytics_keeps_supported_answers_distinct() -> None:
    analytics = build_feedback_analytics(
        answer="Grounded answer",
        confidence=0.82,
        sources=["KB KB-1: Reset password"],
        reasoning="Grounded answer using 1 KB entry.",
        mode="kb_answer",
    )

    assert analytics["source_count"] == 1
    assert analytics["low_confidence"] is False
    assert analytics["no_sources"] is False
    assert analytics["fallback_only"] is False
    assert analytics["reasoning_summary"] == "Grounded answer using 1 KB entry."
