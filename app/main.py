"""FastAPI app: English Notes Coach."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db
from .notes_source import AppleScriptReader, NoteStoreReader, get_reader
from .pron.engine import analyze
from .sync import sync_folders

app = FastAPI(title="English Notes Coach")
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"]
)
db.init()


@lru_cache(maxsize=5000)
def _analyze_cached(text: str) -> str:
    return json.dumps(analyze(text))


def analysis(text: str) -> list[dict]:
    return json.loads(_analyze_cached(text))


class FolderIn(BaseModel):
    name: str


class SyncIn(BaseModel):
    folders: list[str] | None = None


class ItemPatch(BaseModel):
    status: str | None = None
    comment: str | None = None


class AnalyzeIn(BaseModel):
    text: str


class AnalyzeBatchIn(BaseModel):
    texts: list[str]


@app.get("/api/status")
def status():
    fda = NoteStoreReader.available()
    return {
        "reader": "notestore" if fda else "applescript",
        "full_disk_access": fda,
        "highlight_supported": fda,
    }


@app.get("/api/apple-folders")
def apple_folders():
    try:
        folders = get_reader().list_folders()
    except Exception:  # noqa: BLE001 - fall back to AppleScript listing
        folders = AppleScriptReader().list_folders()
    return [f.__dict__ for f in folders]


@app.get("/api/folders")
def list_folders():
    with db.connect() as con:
        rows = con.execute("""
            SELECT f.*, 
              (SELECT COUNT(*) FROM notes n WHERE n.folder = f.name) AS notes,
              (SELECT COUNT(*) FROM items i WHERE i.folder = f.name AND i.active AND i.kind='vocab') AS vocab,
              (SELECT COUNT(*) FROM items i WHERE i.folder = f.name AND i.active AND i.kind='mistake') AS mistakes
            FROM folders f ORDER BY f.added_at
        """).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/folders")
def add_folder(body: FolderIn):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "folder name required")
    with db.connect() as con:
        con.execute("INSERT OR IGNORE INTO folders (name, added_at) VALUES (?, ?)", (name, db.now()))
    return {"ok": True}


@app.delete("/api/folders/{name}")
def remove_folder(name: str):
    with db.connect() as con:
        con.execute("DELETE FROM folders WHERE name = ?", (name,))
        con.execute("DELETE FROM notes WHERE folder = ?", (name,))
        con.execute("UPDATE items SET active = 0 WHERE folder = ?", (name,))
    return {"ok": True}


@app.post("/api/sync")
def sync(body: SyncIn):
    try:
        return sync_folders(body.folders)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"sync failed: {exc}") from exc


def _item_out(row: dict, with_analysis: bool = True) -> dict:
    d = dict(row)
    if with_analysis:
        d["analysis"] = analysis(d["text"])
    return d


@app.get("/api/items")
def list_items(kind: str | None = None, status: str | None = None,
               folder: str | None = None, q: str | None = None):
    sql = """SELECT i.*, n.title AS note_title FROM items i
             LEFT JOIN notes n ON n.id = i.note_id WHERE i.active = 1"""
    args: list = []
    for col, val in (("i.kind", kind), ("i.status", status), ("i.folder", folder)):
        if val:
            sql += f" AND {col} = ?"
            args.append(val)
    if q:
        sql += " AND (i.text LIKE ? OR i.context LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY i.folder, n.title, i.position"
    with db.connect() as con:
        rows = con.execute(sql, args).fetchall()
    return [_item_out(r) for r in rows]


@app.patch("/api/items/{item_id}")
def update_item(item_id: str, body: ItemPatch):
    sets, args = [], []
    if body.status is not None:
        if body.status not in db.STATUSES:
            raise HTTPException(400, f"status must be one of {db.STATUSES}")
        sets.append("status = ?")
        args.append(body.status)
    if body.comment is not None:
        sets.append("comment = ?")
        args.append(body.comment)
    if not sets:
        raise HTTPException(400, "nothing to update")
    sets.append("updated_at = ?")
    args += [db.now(), item_id]
    with db.connect() as con:
        cur = con.execute(f"UPDATE items SET {', '.join(sets)} WHERE id = ?", args)
        if cur.rowcount == 0:
            raise HTTPException(404, "item not found")
        row = con.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return _item_out(row)


@app.get("/api/notes")
def list_notes(folder: str | None = None):
    sql = """SELECT n.id, n.folder, n.title, n.modified,
               (SELECT COUNT(*) FROM items i WHERE i.note_id = n.id AND i.active AND i.kind='vocab') AS vocab,
               (SELECT COUNT(*) FROM items i WHERE i.note_id = n.id AND i.active AND i.kind='mistake') AS mistakes
             FROM notes n"""
    args = []
    if folder:
        sql += " WHERE n.folder = ?"
        args.append(folder)
    sql += " ORDER BY n.folder, n.title"
    with db.connect() as con:
        return [dict(r) for r in con.execute(sql, args)]


@app.get("/api/notes/{note_id:path}")
def get_note(note_id: str):
    with db.connect() as con:
        n = con.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not n:
            raise HTTPException(404, "note not found")
        items = con.execute(
            "SELECT * FROM items WHERE note_id = ? AND active = 1 ORDER BY position", (note_id,)
        ).fetchall()
    d = dict(n)
    d["runs"] = json.loads(d["runs"])
    d["items"] = [_item_out(r, with_analysis=False) for r in items]
    return d


@app.post("/api/analyze")
def analyze_text(body: AnalyzeIn):
    text = body.text.strip()
    if not text:
        return []
    if len(text) > 5000:
        raise HTTPException(400, "text too long (max 5000 chars)")
    return analysis(text)


@app.post("/api/analyze-batch")
def analyze_batch(body: AnalyzeBatchIn):
    return [analysis(t.strip()[:2000]) if t.strip() else [] for t in body.texts[:200]]


# Serve the built frontend if present (production mode).
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = _DIST / path
        return FileResponse(f if path and f.is_file() else _DIST / "index.html")
