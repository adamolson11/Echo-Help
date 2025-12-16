import os
from pathlib import Path

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

from backend.app import models

# Allow configuring the DB path via env var to support Docker volumes.
# Default to repo-root `echohelp.db` for local dev.
BASE_DIR = Path(__file__).resolve().parents[2]

# Track current DB path so we can refresh the engine if tests change
# `ECHOHELP_DB_PATH` between imports.
_DB_PATH = None
DATABASE_URL = None
engine = None


def _lazy_session_local(*args, **kwargs):
    """Lazily create a sessionmaker bound to the current engine on first use.
    This allows tests that call `SessionLocal()` before the engine has been
    eagerly created to still obtain a bound Session. When the engine is
    (re)created via `ensure_engine()` it will overwrite `SessionLocal` with
    the canonical sessionmaker.
    """
    ensure_engine()
    global SessionLocal
    # If a proper sessionmaker has already been assigned, call it.
    if SessionLocal is not None and hasattr(SessionLocal, "class_"):
        return SessionLocal(*args, **kwargs)
    # Otherwise create and cache a new sessionmaker bound to the engine.
    SessionLocal = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return SessionLocal(*args, **kwargs)


# Exported symbol: callers should call `SessionLocal()` to get a session.
SessionLocal = _lazy_session_local


def _make_engine(db_path: str):
    url = f"sqlite:///{db_path}"
    return create_engine(url, echo=False, connect_args={"check_same_thread": False})


def ensure_engine():
    """Ensure the module-level `engine` is created for the current
    `ECHOHELP_DB_PATH`. If the env var changed since the engine was
    created, recreate the engine to point at the new DB file.
    """
    global _DB_PATH, DATABASE_URL, engine
    desired = os.getenv("ECHOHELP_DB_PATH", str(BASE_DIR / "echohelp.db"))
    if engine is None or _DB_PATH != desired:
        _DB_PATH = desired
        DATABASE_URL = f"sqlite:///{_DB_PATH}"
        engine = _make_engine(_DB_PATH)
        # Create a session factory bound to the engine so callers
        # can obtain Sessions that are properly bound. Recreate
        # SessionLocal whenever the engine changes (tests set a
        # new ECHOHELP_DB_PATH at runtime).
        global SessionLocal
        SessionLocal = sessionmaker(
            bind=engine,
            class_=Session,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        # When we (re)create the engine because the DB path changed,
        # ensure model classes are imported and the schema exists on
        # the new engine. This keeps tests deterministic when they
        # set `ECHOHELP_DB_PATH` at module import time.
        try:
            from . import models  # noqa: F401

            SQLModel.metadata.create_all(engine)
        except Exception:
            # Non-fatal; if creation fails later init_db() will attempt again.
            pass


def init_db():
    ensure_engine()
    # Ensure all SQLModel classes are registered on metadata and
    # create tables unconditionally for the current engine. Do not
    # swallow exceptions here so test failures surface immediately
    # when table creation cannot complete.
    SQLModel.metadata.create_all(engine)

    # Lightweight migration for added KB columns on `ticket` table.
    # If the database existed before we added `short_id`, `body_md`,
    # `root_cause`, `environment`, or `tags`, create those columns.
    try:
        import sqlite3

        # Only apply for SQLite file DBs
        if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
            db_path = _DB_PATH
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            def _get_cols(table: str) -> list[str]:
                cur.execute(f"PRAGMA table_info({table})")
                return [r[1] for r in cur.fetchall()]

            def _add_col_if_missing(*, table: str, col_def: str, col_name: str):
                cols = _get_cols(table)
                if col_name not in cols:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")

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

            # Lightweight migration for Ask Echo reasoning/audit fields.
            # Older DBs may have `askecholog` without these columns.

            _add_col_if_missing(
                table="askecholog",
                col_def="candidate_snippet_ids_json TEXT",
                col_name="candidate_snippet_ids_json",
            )
            _add_col_if_missing(
                table="askecholog",
                col_def="chosen_snippet_ids_json TEXT",
                col_name="chosen_snippet_ids_json",
            )
            _add_col_if_missing(table="askecholog", col_def="echo_score REAL", col_name="echo_score")
            _add_col_if_missing(
                table="askecholog", col_def="reasoning_notes TEXT", col_name="reasoning_notes"
            )

            # Ticket feedback has grown new columns over time; older DBs may be missing them.
            _add_col_if_missing(table="ticketfeedback", col_def="helped BOOLEAN", col_name="helped")
            _add_col_if_missing(
                table="ticketfeedback", col_def="resolution_notes TEXT", col_name="resolution_notes"
            )
            _add_col_if_missing(table="ticketfeedback", col_def="ai_cluster_id TEXT", col_name="ai_cluster_id")
            _add_col_if_missing(table="ticketfeedback", col_def="ai_summary TEXT", col_name="ai_summary")

            # Snippet tables: keep older DBs compatible with newer snippet fields.
            _add_col_if_missing(table="solutionsnippet", col_def="summary TEXT", col_name="summary")
            _add_col_if_missing(table="solutionsnippet", col_def="content_md TEXT", col_name="content_md")
            _add_col_if_missing(table="solutionsnippet", col_def="source TEXT", col_name="source")
            _add_col_if_missing(table="solutionsnippet", col_def="echo_score REAL", col_name="echo_score")
            _add_col_if_missing(table="solutionsnippet", col_def="success_count INTEGER", col_name="success_count")
            _add_col_if_missing(table="solutionsnippet", col_def="failure_count INTEGER", col_name="failure_count")
            _add_col_if_missing(table="solutionsnippet", col_def="tags TEXT", col_name="tags")
            _add_col_if_missing(table="solutionsnippet", col_def="updated_at TEXT", col_name="updated_at")

            _add_col_if_missing(table="snippetfeedback", col_def="notes TEXT", col_name="notes")

            # Embeddings table: model + created_at were added after early iterations.
            _add_col_if_missing(table="embedding", col_def="model_name TEXT", col_name="model_name")
            _add_col_if_missing(table="embedding", col_def="created_at TEXT", col_name="created_at")

            conn.commit()
            conn.close()
    except Exception:
        # Non-fatal migration helper — if it fails, existing schema will be used.
        pass


def get_session():
    ensure_engine()
    # Use the canonical SessionLocal so sessions are bound to the
    # current engine. SessionLocal will be recreated in ensure_engine
    # whenever the engine changes.
    global SessionLocal
    if SessionLocal is None:
        # fallback: ensure engine and SessionLocal exist
        ensure_engine()
    with SessionLocal() as session:
        yield session
