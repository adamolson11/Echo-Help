from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app.db_init import seed_tickets
from scripts.seed_demo_org import seed_demo_org


@pytest.mark.parametrize(
    ("query", "expected_tokens"),
    [
        ("I need a password reset", ("password reset", "reset password")),
        ("forgot my password", ("password reset", "forgot password")),
        ("can't log in", ("log in", "login", "password reset", "account")),
    ],
)
def test_ask_echo_common_support_phrases_surface_auth_tickets(
    query: str,
    expected_tokens: tuple[str, ...],
) -> None:
    seed_tickets()
    seed_demo_org()

    client = TestClient(app)
    response = client.post("/api/ask-echo", json={"q": query, "limit": 5})

    assert response.status_code == 200
    data = response.json()

    tickets = data.get("suggested_tickets") or []
    snippets = data.get("suggested_snippets") or []
    assert tickets or snippets

    combined_text = " ".join(
        [
            *((item.get("title") or item.get("summary") or "") for item in tickets if isinstance(item, dict)),
            *((item.get("title") or item.get("summary") or "") for item in snippets if isinstance(item, dict)),
        ]
    ).lower()

    assert any(token in combined_text for token in expected_tokens)