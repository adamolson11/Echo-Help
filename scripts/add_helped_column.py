#!/usr/bin/env python3
"""
Safe one-off script to add `helped` column to `ticketfeedback`
if it does not already exist. Run from repo root:

    python3 scripts/add_helped_column.py

This is non-destructive and will only ALTER TABLE ADD COLUMN if needed.
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
if "helped" in cols:
    print("Column 'helped' already present.")
else:
    print("Adding column 'helped' to ticketfeedback...")
    # Use INTEGER to represent boolean (NULL/0/1)
    cur.execute("ALTER TABLE ticketfeedback ADD COLUMN helped INTEGER")
    conn.commit()
    print("Done.")

conn.close()
