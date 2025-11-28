from backend.app.services.confidence_calculator import calculate_echo_score
from types import SimpleNamespace


def make_snippet(success=0, failure=0, days_old=None):
    # create a simple object with attributes used by the calculator
    s = SimpleNamespace()
    s.success_count = success
    s.failure_count = failure
    from datetime import datetime, timedelta, timezone

    if days_old is None:
        s.updated_at = datetime.now(timezone.utc)
    else:
        s.updated_at = datetime.now(timezone.utc) - timedelta(days=days_old)
    s.created_at = s.updated_at
    return s


def test_score_improves_with_more_successes():
    a = make_snippet(success=0, failure=0)
    b = make_snippet(success=3, failure=0)
    assert calculate_echo_score(b) > calculate_echo_score(a)


def test_score_penalizes_failures():
    a = make_snippet(success=2, failure=0)
    b = make_snippet(success=2, failure=3)
    assert calculate_echo_score(b) < calculate_echo_score(a)


def test_score_stable_for_low_data():
    a = make_snippet(success=0, failure=0)
    b = make_snippet(success=1, failure=0)
    # small improvement but not extreme
    assert 0 <= calculate_echo_score(a) <= 1
    assert 0 <= calculate_echo_score(b) <= 1
    assert calculate_echo_score(b) - calculate_echo_score(a) < 0.6
