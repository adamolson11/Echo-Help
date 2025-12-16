#!/usr/bin/env python3
"""Safe one-off script to create the `embedding` table in the SQLite DB.

This script checks whether the table exists and only creates it when
missing. It uses the application's engine so SQLModel metadata is created
consistently with the rest of the app.
"""
import sqlite3
import os

from sqlmodel import SQLModel

import backend.app.db as db
from backend.app.models.embedding import Embedding  # noqa: F401

DB_PATH = os.getenv("ECHOHELP_DB_PATH", "echohelp.db")


def main() -> None:
    db.ensure_engine()
    if db.engine is None:
        raise SystemExit("Database engine is not initialized")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='embedding'")
    exists = cursor.fetchone()

    expected_cols = {
        "id",
        "ticket_id",
        "feedback_id",
        "text",
        "vector",
        "model_name",
        "created_at",
    }

    if not exists:
        print("Creating table 'embedding'...")
        # Use the app engine so tables are created where the app expects them.
        SQLModel.metadata.create_all(db.engine)
        print("Done.")
    else:
        # Check for missing columns and add them non-destructively.
        cursor.execute("PRAGMA table_info('embedding')")
        rows = cursor.fetchall()
        existing = {row[1] for row in rows}
        missing = expected_cols - existing
        if not missing:
            print("Table 'embedding' already exists and is up-to-date.")
        else:
            print("Table 'embedding' exists; adding missing columns:", missing)
            for col in missing:
                if col in ("ticket_id", "feedback_id"):
                    sql = f"ALTER TABLE embedding ADD COLUMN {col} INTEGER"
                elif col == "vector":
                    sql = f"ALTER TABLE embedding ADD COLUMN {col} TEXT"
                elif col == "created_at":
                    sql = f"ALTER TABLE embedding ADD COLUMN {col} TEXT"
                else:
                    sql = f"ALTER TABLE embedding ADD COLUMN {col} TEXT"
                cursor.execute(sql)
            conn.commit()
            print("Added missing columns.")

    conn.close()


if __name__ == "__main__":
    main()
