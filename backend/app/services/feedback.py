from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock


@dataclass(frozen=True)
class FeedbackRecord:
    question: str
    answer: str
    rating: int


_feedback_lock = Lock()
_feedback_records: list[FeedbackRecord] = []


def record_feedback(question: str, answer: str, rating: int) -> None:
    record = FeedbackRecord(
        question=(question or "").strip(),
        answer=(answer or "").strip(),
        rating=int(rating),
    )
    with _feedback_lock:
        _feedback_records.append(record)


def list_recorded_feedback() -> list[dict[str, object]]:
    with _feedback_lock:
        return [asdict(record) for record in _feedback_records]


def clear_recorded_feedback() -> None:
    with _feedback_lock:
        _feedback_records.clear()
