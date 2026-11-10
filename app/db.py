"""App database (SQLite). Apple Notes itself is never modified."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("APP_DB", Path(__file__).resolve().parent.parent / "data" / "app.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS folders (
    name TEXT PRIMARY KEY,
    added_at TEXT NOT NULL,
    last_synced TEXT,
    last_source TEXT
);
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    folder TEXT NOT NULL,
    title TEXT NOT NULL,
    modified TEXT,
    text TEXT NOT NULL,
    runs TEXT NOT NULL,
    synced_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL,
    folder TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('vocab', 'mistake')),
    text TEXT NOT NULL,
    context TEXT NOT NULL,
    ctx_start INTEGER NOT NULL,
    ctx_end INTEGER NOT NULL,
    position INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    comment TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS items_note ON items(note_id);
CREATE INDEX IF NOT EXISTS items_kind ON items(kind, status);
"""

STATUSES = ("new", "practicing", "fixed")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init() -> None:
    with connect() as con:
        con.executescript(SCHEMA)


def runs_to_json(runs) -> str:
    return json.dumps([r.__dict__ for r in runs], separators=(",", ":"))
