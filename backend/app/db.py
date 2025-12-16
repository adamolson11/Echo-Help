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
    # Debug: list tables present after create_all (helps diagnose test ordering issues)
    try:
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"init_db: engine DB path={_DB_PATH}, tables={tables}")
    except Exception:
        pass

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
            cur.execute("PRAGMA table_info(askecholog)")
            ask_cols = [r[1] for r in cur.fetchall()]

            def add_ask_col(col_def: str, col_name: str):
                if col_name not in ask_cols:
                    cur.execute(f"ALTER TABLE askecholog ADD COLUMN {col_def}")

            add_ask_col("candidate_snippet_ids_json TEXT", "candidate_snippet_ids_json")
            add_ask_col("chosen_snippet_ids_json TEXT", "chosen_snippet_ids_json")
            add_ask_col("echo_score REAL", "echo_score")
            add_ask_col("reasoning_notes TEXT", "reasoning_notes")

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
