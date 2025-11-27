#!/usr/bin/env python3
"""
Safe one-off script to add `resolution_notes` column to `ticketfeedback`
if it does not already exist. Run from repo root:

    python3 scripts/add_resolution_notes_column.py
"""

import sqlite3
from pathlib import Path

DB = Path("./echohelp.db")
if not DB.exists():
    print("Database file not found:", DB)
    raise SystemExit(1)

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

cur.execute("PRAGMA table_info('ticketfeedback')")
cols = [r[1] for r in cur.fetchall()]
if "resolution_notes" in cols:
    print("Column 'resolution_notes' already present.")
else:
    print("Adding column 'resolution_notes' to ticketfeedback...")
    cur.execute("ALTER TABLE ticketfeedback ADD COLUMN resolution_notes TEXT")
    conn.commit()
    print("Done.")

conn.close()
