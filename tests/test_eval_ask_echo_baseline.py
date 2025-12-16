from scripts.eval_ask_echo_baseline import confusion_for, grid_search_threshold


def test_confusion_for_simple_thresholds() -> None:
    rows = [
        {"label_helped": True, "features": {"ticket": {"top_score": 0.9}, "snippet": {"top_echo_score": 0.0}}},
        {"label_helped": True, "features": {"ticket": {"top_score": 0.1}, "snippet": {"top_echo_score": 0.9}}},
        {"label_helped": False, "features": {"ticket": {"top_score": 0.0}, "snippet": {"top_echo_score": 0.0}}},
        {"label_helped": False, "features": {"ticket": {"top_score": 0.9}, "snippet": {"top_echo_score": 0.0}}},
    ]

    c = confusion_for(rows, ticket_threshold=0.6, snippet_threshold=0.8)
    assert (c.tp, c.fp, c.tn, c.fn) == (2, 1, 1, 0)
    assert c.f1() == 0.8


def test_grid_search_threshold_finds_reasonable_best() -> None:
    rows = [
        {"label_helped": True, "features": {"ticket": {"top_score": 0.9}, "snippet": {"top_echo_score": 0.0}}},
        {"label_helped": True, "features": {"ticket": {"top_score": 0.1}, "snippet": {"top_echo_score": 0.9}}},
        {"label_helped": False, "features": {"ticket": {"top_score": 0.0}, "snippet": {"top_echo_score": 0.0}}},
        {"label_helped": False, "features": {"ticket": {"top_score": 0.9}, "snippet": {"top_echo_score": 0.0}}},
    ]

    bt, bs, best = grid_search_threshold(rows)
    assert 0.0 <= bt <= 1.0
    assert 0.0 <= bs <= 1.0
    assert best.total == 4
    # Best possible F1 here is 0.8 because one negative has a high ticket score.
    assert best.f1() == 0.8
