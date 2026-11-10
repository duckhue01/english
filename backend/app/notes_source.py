"""Read Apple Notes with formatting.

Two backends produce the same `RawNote` shape (plain text + attribute runs):

* ``NoteStoreReader`` reads ``NoteStore.sqlite`` directly (needs Full Disk
  Access). This is the only way to see **highlights**, which AppleScript drops.
* ``AppleScriptReader`` uses ``osascript`` HTML bodies (no special permission;
  sees underline / bold / strikethrough / headings, but not highlight).
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import tempfile
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

log = logging.getLogger(__name__)

NOTES_DIR = Path.home() / "Library/Group Containers/group.com.apple.notes"
NOTES_DB = NOTES_DIR / "NoteStore.sqlite"
APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
OBJ_CHAR = "\ufffc"  # attachment placeholder in note text

# AttributeRun field numbers (see apple_cloud_notes_parser notestore.proto).
F_LENGTH, F_PARA, F_WEIGHT, F_UNDERLINE, F_STRIKE, F_LINK = 1, 2, 5, 6, 7, 9
F_ATTACHMENT = 12
# Highlight ("emphasis") colour. Overridable once verified against real data.
F_HIGHLIGHT = int(os.environ.get("NOTES_HIGHLIGHT_FIELD", "14"))


@dataclass
class Run:
    start: int
    end: int
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    highlight: int = 0  # 0 = none, otherwise colour id
    heading: int = 0  # 0 body, 1 title, 2 heading, 3 subheading
    link: str | None = None


@dataclass
class RawNote:
    id: str
    title: str
    folder: str
    modified: str
    text: str
    runs: list[Run] = field(default_factory=list)


@dataclass
class FolderInfo:
    name: str
    account: str
    note_count: int


# --------------------------------------------------------------------------
# Minimal protobuf decoding (no schema needed)
# --------------------------------------------------------------------------

def _varint(buf: bytes, i: int) -> tuple[int, int]:
    shift = result = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, i
        shift += 7


def pb_decode(buf: bytes) -> dict[int, list]:
    """Decode one protobuf message into {field: [values]} (bytes or int)."""
    out: dict[int, list] = {}
    i = 0
    n = len(buf)
    while i < n:
        key, i = _varint(buf, i)
        fno, wt = key >> 3, key & 7
        if wt == 0:
            val, i = _varint(buf, i)
        elif wt == 2:
            ln, i = _varint(buf, i)
            val = buf[i:i + ln]
            i += ln
        elif wt == 1:
            val = int.from_bytes(buf[i:i + 8], "little")
            i += 8
        elif wt == 5:
            val = int.from_bytes(buf[i:i + 4], "little")
            i += 4
        else:
            raise ValueError(f"unsupported wire type {wt}")
        out.setdefault(fno, []).append(val)
    return out


def _first(d: dict, f: int, default=None):
    v = d.get(f)
    return v[0] if v else default


def _decompress(data: bytes) -> bytes:
    if data[:2] == b"\x1f\x8b":
        return gzip.decompress(data)
    try:
        return zlib.decompress(data)
    except zlib.error:
        return data


def _highlight_value(v) -> int:
    if isinstance(v, int):
        return v
    return 1 if v else 0  # embedded message => highlighted


def parse_note_blob(data: bytes) -> tuple[str, list[Run], list[dict]]:
    """Return (text, runs, raw_runs) from a ZICNOTEDATA.ZDATA blob."""
    store = pb_decode(_decompress(data))
    doc = pb_decode(_first(store, 2, b""))
    note = pb_decode(_first(doc, 3, b""))
    text = _first(note, 2, b"").decode("utf-8", errors="replace")
    utf16 = text.encode("utf-16-le")

    runs: list[Run] = []
    raw_runs: list[dict] = []
    pos16 = 0
    pos = 0  # python str index
    for raw in note.get(5, []):
        ar = pb_decode(raw)
        raw_runs.append({k: (v if isinstance(v[0], int) else "<bytes>") for k, v in ar.items()})
        ln16 = _first(ar, F_LENGTH, 0)
        seg = utf16[pos16 * 2:(pos16 + ln16) * 2].decode("utf-16-le", errors="replace")
        start, end = pos, pos + len(seg)
        pos16 += ln16
        pos = end

        weight = _first(ar, F_WEIGHT, 0)
        heading = 0
        para = _first(ar, F_PARA)
        if para:
            style = _first(pb_decode(para), 1, -1)
            heading = {0: 1, 1: 2, 2: 3}.get(style, 0)
        link = _first(ar, F_LINK)
        runs.append(Run(
            start, end,
            bold=weight in (1, 3),
            italic=weight in (2, 3),
            underline=bool(_first(ar, F_UNDERLINE, 0)),
            strike=bool(_first(ar, F_STRIKE, 0)),
            highlight=_highlight_value(_first(ar, F_HIGHLIGHT, 0)),
            heading=heading,
            link=link.decode("utf-8", "replace") if isinstance(link, bytes) else None,
        ))
    return text, runs, raw_runs


class NoteStoreReader:
    """Reads a snapshot copy of NoteStore.sqlite (never touches the original)."""

    name = "notestore"

    @staticmethod
    def available() -> bool:
        try:
            with open(NOTES_DB, "rb"):
                return True
        except OSError:
            return False

    def _connect(self) -> tuple[sqlite3.Connection, str]:
        tmp = tempfile.mkdtemp(prefix="notes-snap-")
        for suffix in ("", "-wal", "-shm"):
            src = Path(str(NOTES_DB) + suffix)
            if src.exists():
                shutil.copy2(src, Path(tmp) / src.name)
        con = sqlite3.connect(Path(tmp) / NOTES_DB.name)
        con.row_factory = sqlite3.Row
        return con, tmp

    @staticmethod
    def _cols(con: sqlite3.Connection) -> set[str]:
        return {r[1] for r in con.execute("PRAGMA table_info(ZICCLOUDSYNCINGOBJECT)")}

    def list_folders(self) -> list[FolderInfo]:
        con, tmp = self._connect()
        try:
            cols = self._cols(con)
            trash = "AND (f.ZFOLDERTYPE IS NULL OR f.ZFOLDERTYPE != 1)" if "ZFOLDERTYPE" in cols else ""
            rows = con.execute(f"""
                SELECT f.ZTITLE2 AS name, COALESCE(a.ZNAME, '') AS account,
                       (SELECT COUNT(*) FROM ZICCLOUDSYNCINGOBJECT n
                         WHERE n.ZFOLDER = f.Z_PK AND n.ZTITLE1 IS NOT NULL
                           AND COALESCE(n.ZMARKEDFORDELETION, 0) = 0) AS cnt
                FROM ZICCLOUDSYNCINGOBJECT f
                LEFT JOIN ZICCLOUDSYNCINGOBJECT a ON a.Z_PK = f.ZOWNER
                WHERE f.ZTITLE2 IS NOT NULL AND COALESCE(f.ZMARKEDFORDELETION, 0) = 0 {trash}
                ORDER BY f.ZTITLE2
            """).fetchall()
            return [FolderInfo(r["name"], r["account"], r["cnt"]) for r in rows]
        finally:
            con.close()
            shutil.rmtree(tmp, ignore_errors=True)

    def read_folder(self, folder: str) -> list[RawNote]:
        con, tmp = self._connect()
        try:
            cols = self._cols(con)
            locked = "AND COALESCE(n.ZISPASSWORDPROTECTED, 0) = 0" if "ZISPASSWORDPROTECTED" in cols else ""
            rows = con.execute(f"""
                SELECT n.ZIDENTIFIER AS id, n.ZTITLE1 AS title,
                       n.ZMODIFICATIONDATE1 AS modified, f.ZTITLE2 AS folder, d.ZDATA AS data
                FROM ZICCLOUDSYNCINGOBJECT n
                JOIN ZICCLOUDSYNCINGOBJECT f ON f.Z_PK = n.ZFOLDER
                JOIN ZICNOTEDATA d ON d.ZNOTE = n.Z_PK
                WHERE f.ZTITLE2 = ? AND n.ZTITLE1 IS NOT NULL
                  AND COALESCE(n.ZMARKEDFORDELETION, 0) = 0 {locked}
            """, (folder,)).fetchall()
            notes = []
            for r in rows:
                if not r["data"]:
                    continue
                try:
                    text, runs, _ = parse_note_blob(r["data"])
                except Exception as exc:  # noqa: BLE001
                    log.warning("skip note %s: %s", r["title"], exc)
                    continue
                mod = (APPLE_EPOCH + timedelta(seconds=r["modified"] or 0)).isoformat()
                notes.append(RawNote(r["id"], r["title"], r["folder"], mod, text, runs))
            return notes
        finally:
            con.close()
            shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# AppleScript fallback
# --------------------------------------------------------------------------

_JXA_FOLDERS = """
const Notes = Application('Notes');
const out = [];
Notes.accounts().forEach(a => a.folders().forEach(f => {
  out.push({name: f.name(), account: a.name(), count: f.notes.length});
}));
JSON.stringify(out);
"""

_JXA_NOTES = """
function run(argv) {
  const Notes = Application('Notes');
  const out = [];
  Notes.accounts().forEach(a => a.folders().forEach(f => {
    if (f.name() !== argv[0]) return;
    f.notes().forEach(n => {
      try {
        if (n.passwordProtected()) return;
        out.push({id: n.id(), title: n.name(), folder: f.name(),
                  modified: n.modificationDate().toISOString(), body: n.body()});
      } catch (e) {}
    });
  }));
  return JSON.stringify(out);
}
"""


def _jxa(script: str, *args: str) -> str:
    res = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script, *args],
        capture_output=True, text=True, timeout=300,
    )
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "osascript failed")
    return res.stdout


class _HtmlToRuns(HTMLParser):
    BLOCK = {"div", "p", "h1", "h2", "h3", "li", "tr", "br"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.len = 0
        self.runs: list[Run] = []
        self.stack: list[str] = []
        self.skip = 0

    def _state(self) -> Run:
        s = self.stack
        heading = 1 if "h1" in s else 2 if "h2" in s else 3 if "h3" in s else 0
        return Run(0, 0, bold="b" in s or "strong" in s, italic="i" in s or "em" in s,
                   underline="u" in s, strike="strike" in s or "s" in s,
                   highlight=1 if "mark" in s else 0, heading=heading)

    def _emit(self, chunk: str) -> None:
        if not chunk:
            return
        r = self._state()
        r.start, r.end = self.len, self.len + len(chunk)
        self.text.append(chunk)
        self.len = r.end
        self.runs.append(r)

    def _newline(self) -> None:
        if self.text and not "".join(self.text[-1:]).endswith("\n"):
            self._emit("\n")

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self._emit(OBJ_CHAR)
            return
        if tag == "table":
            self._newline()
            self._emit(OBJ_CHAR)
            self.skip += 1
            return
        if tag == "br":
            self._emit("\n")
            return
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "table":
            self.skip -= 1
            return
        if tag in self.stack:
            idx = len(self.stack) - 1 - self.stack[::-1].index(tag)
            del self.stack[idx]
        if tag in self.BLOCK and not self.skip:
            self._newline()

    def handle_data(self, data):
        if self.skip:
            return
        self._emit(data.replace("\r", "").replace("\n", ""))


def html_to_runs(html: str) -> tuple[str, list[Run]]:
    p = _HtmlToRuns()
    p.feed(html)
    text = "".join(p.text)
    return text, p.runs


class AppleScriptReader:
    name = "applescript"

    def list_folders(self) -> list[FolderInfo]:
        data = json.loads(_jxa(_JXA_FOLDERS))
        return [FolderInfo(d["name"], d["account"], d["count"]) for d in data]

    def read_folder(self, folder: str) -> list[RawNote]:
        data = json.loads(_jxa(_JXA_NOTES, folder))
        notes = []
        for d in data:
            text, runs = html_to_runs(d["body"])
            notes.append(RawNote(d["id"], d["title"], d["folder"], d["modified"], text, runs))
        return notes


def get_reader():
    return NoteStoreReader() if NoteStoreReader.available() else AppleScriptReader()
