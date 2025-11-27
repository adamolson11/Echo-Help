from backend.app.ai.normalize import normalize_phrase


def test_normalize_phrase_basic():
    assert normalize_phrase("  RESET   password!! ") == "reset password"
