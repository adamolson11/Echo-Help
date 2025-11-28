from pathlib import Path
import os

from sqlmodel import Session, SQLModel, create_engine

# Allow configuring the DB path via env var to support Docker volumes.
# Default to repo-root `echohelp.db` for local dev.
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = os.getenv("ECHOHELP_DB_PATH", str(BASE_DIR / "echohelp.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db():
    try:
        SQLModel.metadata.create_all(engine)
    except Exception:
        # In some dev environments the metadata may attempt to create
        # tables that already exist (or duplicate entries). Swallow
        # exceptions here to allow lightweight migrations to continue.
        pass

    # Lightweight migration for added KB columns on `ticket` table.
    # If the database existed before we added `short_id`, `body_md`,
    # `root_cause`, `environment`, or `tags`, create those columns.
    try:
        import sqlite3

        # Only apply for SQLite file DBs
        if DATABASE_URL.startswith("sqlite"):
            db_path = DB_PATH
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(ticket)")
            cols = [r[1] for r in cur.fetchall()]

            def add_col(col_def: str, col_name: str):
                if col_name not in cols:
                    cur.execute(f"ALTER TABLE ticket ADD COLUMN {col_def}")

            add_col("short_id TEXT", "short_id")
            add_col("body_md TEXT", "body_md")
            add_col("root_cause TEXT", "root_cause")
            add_col("environment TEXT", "environment")
            add_col("tags TEXT", "tags")
            conn.commit()
            conn.close()
    except Exception:
        # Non-fatal migration helper — if it fails, existing schema will be used.
        pass


def get_session():
    with Session(engine) as session:
        yield session
