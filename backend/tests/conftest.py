import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def _isolate_db_per_test(monkeypatch: pytest.MonkeyPatch):
    td = tempfile.NamedTemporaryFile(prefix="echohelp_backend_test_", suffix=".db", delete=False)
    td.close()
    monkeypatch.setenv("ECHOHELP_DB_PATH", td.name)
    yield
    try:
        os.remove(td.name)
    except FileNotFoundError:
        pass
