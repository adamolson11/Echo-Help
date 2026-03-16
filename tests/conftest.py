import os
import tempfile

# Force the fallback (hash-based) embedding path in all tests so that
# the test suite never tries to download the sentence-transformers model
# from huggingface.co.  This must be set before any backend module that
# imports `backend.app.services.embeddings` is imported.
os.environ.setdefault("ECHO_EMBEDDINGS", "off")

import pytest


@pytest.fixture(autouse=True)
def _isolate_db_per_test(monkeypatch: pytest.MonkeyPatch):
    """Ensure every test runs against a fresh, isolated SQLite database.

    Many tests assume a clean DB (no prior tickets/feedback/logs). Using a
    per-test temp DB eliminates state leakage and ordering dependence.

    This must run before any code under test calls `init_db()` or `SessionLocal()`.
    """
    td = tempfile.NamedTemporaryFile(prefix="echohelp_test_", suffix=".db", delete=False)
    td.close()
    monkeypatch.setenv("ECHOHELP_DB_PATH", td.name)
    yield
    try:
        os.remove(td.name)
    except FileNotFoundError:
        pass
