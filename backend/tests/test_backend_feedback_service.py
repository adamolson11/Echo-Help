import json

from backend.app.db import SessionLocal, init_db
from backend.app.models.ask_echo_feedback import AskEchoFeedback
from backend.app.models.ask_echo_log import AskEchoLog
from backend.app.services.feedback import build_feedback_analytics, list_feedback_records, normalize_sources


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


def test_normalize_sources_dedupes_strips_and_preserves_order() -> None:
    normalized = normalize_sources(
        [
            "  KB KB-1: Reset password  ",
            "",
            "Ticket #4: VPN failure",
            "KB KB-1:   Reset password",
            "   ",
            "Ticket #4: VPN failure",
            "KB KB-2: MFA reset",
        ]
    )

    assert normalized == [
        "KB KB-1: Reset password",
        "Ticket #4: VPN failure",
        "KB KB-2: MFA reset",
    ]


def test_list_feedback_records_falls_back_to_reasoning_notes_when_log_fields_missing() -> None:
    init_db()

    with SessionLocal() as session:
        log = AskEchoLog(
            query="fallback computation check",
            answer_text="",
            kb_confidence=0.0,
            mode="general_answer",
            source_count=0,
            reasoning_summary=None,
            low_confidence=False,
            no_sources=False,
            fallback_only=False,
            feedback_status="pending",
            feedback_rating=0,
            reasoning_notes=json.dumps(
                {
                    "response": {
                        "answer": "  Fallback answer from notes  ",
                        "confidence": 0.0,
                        "sources": ["  Ticket #12: Password reset  ", "Ticket #12: Password reset"],
                        "reasoning": "Fallback answer because no strong KB-backed match was available.",
                    }
                }
            ),
        )
        session.add(log)
        session.commit()
        session.refresh(log)

        session.add(
            AskEchoFeedback(
                ask_echo_log_id=int(log.id or 0),
                helped=False,
                notes="still not useful",
            )
        )
        session.commit()

        records = list_feedback_records(session, limit=10)

    matching = [record for record in records if record["question"] == "fallback computation check"]
    assert len(matching) == 1
    record = matching[0]
    assert record["answer"] == "Fallback answer from notes"
    assert record["sources"] == ["Ticket #12: Password reset"]
    assert record["source_count"] == 1
    assert record["feedback_status"] == "not_helped"
    assert record["rating"] == -1
    assert record["feedback_notes"] == "still not useful"
    assert record["low_confidence"] is True
    assert record["no_sources"] is False
    assert record["fallback_only"] is True
    assert record["reasoning"].startswith("Fallback-only answer.")
