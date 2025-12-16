from backend.app.services.ask_echo_engine import build_ask_echo_features


class _StubSnippet:
    def __init__(self, echo_score: float | None, success_count: int = 0, failure_count: int = 0):
        self.echo_score = echo_score
        self.success_count = success_count
        self.failure_count = failure_count


def test_build_ask_echo_features_shape() -> None:
    feats = build_ask_echo_features(scored_tickets=[(0.7, object()), (0.2, object())], snippets=[_StubSnippet(0.9, 3, 1)])
    assert feats["version"] == "v1"
    assert feats["ticket"]["count"] == 2
    assert feats["ticket"]["top_score"] == 0.7
    assert feats["snippet"]["count"] == 1
    assert feats["snippet"]["top_echo_score"] == 0.9
    assert feats["snippet"]["top_success_count"] == 3
    assert feats["snippet"]["top_failure_count"] == 1


def test_build_ask_echo_features_empty() -> None:
    feats = build_ask_echo_features(scored_tickets=[], snippets=[])
    assert feats["ticket"]["count"] == 0
    assert feats["ticket"]["top_score"] == 0.0
    assert feats["snippet"]["count"] == 0
    assert feats["snippet"]["top_echo_score"] == 0.0
