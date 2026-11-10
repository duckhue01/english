"""Sync selected Apple Notes folders into the app database."""

from __future__ import annotations

from . import db
from .extract import extract_items
from .notes_source import get_reader


def sync_folders(names: list[str] | None = None) -> dict:
    db.init()
    with db.connect() as con:
        if names is None:
            names = [r["name"] for r in con.execute("SELECT name FROM folders")]
    reader = get_reader()
    report = {"source": reader.name, "folders": []}
    for name in names:
        notes = reader.read_folder(name)
        stats = {"folder": name, "notes": len(notes), "vocab": 0, "mistake": 0, "new_items": 0}
        ts = db.now()
        with db.connect() as con:
            con.execute("UPDATE items SET active = 0 WHERE folder = ?", (name,))
            keep_ids = []
            for note in notes:
                keep_ids.append(note.id)
                con.execute(
                    """INSERT INTO notes (id, folder, title, modified, text, runs, synced_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET folder=excluded.folder, title=excluded.title,
                         modified=excluded.modified, text=excluded.text, runs=excluded.runs,
                         synced_at=excluded.synced_at""",
                    (note.id, name, note.title, note.modified, note.text,
                     db.runs_to_json(note.runs), ts),
                )
                for it in extract_items(note.id, note.text, note.runs):
                    stats[it.kind] += 1
                    cur = con.execute(
                        """INSERT INTO items (id, note_id, folder, kind, text, context, ctx_start,
                             ctx_end, position, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(id) DO UPDATE SET folder=excluded.folder,
                             context=excluded.context, ctx_start=excluded.ctx_start,
                             ctx_end=excluded.ctx_end, position=excluded.position, active=1
                           RETURNING created_at""",
                        (it.id, note.id, name, it.kind, it.text, it.context, it.ctx_start,
                         it.ctx_end, it.start, ts, ts),
                    ).fetchone()
                    if cur and cur["created_at"] == ts:
                        stats["new_items"] += 1
            # Notes deleted from Apple Notes disappear from the app (items kept, inactive).
            q = ",".join("?" * len(keep_ids)) or "''"
            con.execute(f"DELETE FROM notes WHERE folder = ? AND id NOT IN ({q})", (name, *keep_ids))
            con.execute(
                "UPDATE folders SET last_synced = ?, last_source = ? WHERE name = ?",
                (ts, reader.name, name),
            )
        report["folders"].append(stats)
    return report
