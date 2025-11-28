from backend.app.db import get_session, init_db
from backend.app.models.embedding import Embedding


def test_embedding_insert():
    # Ensure a clean embedding table for the test run. If an older embedding
    # table exists with an incompatible schema, drop it so we can recreate
    # it using the application's metadata. This keeps the test hermetic.
    import sqlite3

    conn = sqlite3.connect("echohelp.db")
    conn.execute("DROP TABLE IF EXISTS embedding")
    conn.commit()
    conn.close()

    init_db()

    with next(get_session()) as session:
        e = Embedding(text="hello world", vector=[0.1, 0.2])
        session.add(e)
        session.commit()
        session.refresh(e)
        assert e.id is not None
