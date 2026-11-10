"""Turn formatted note text into learning items.

* highlight  -> kind "vocab"   (new vocabulary)
* underline  -> kind "mistake" (pronunciation mistake)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .notes_source import OBJ_CHAR, Run

_WORDCH = re.compile(r"[\w'’\-]")
_SENT_END = re.compile(r"[.!?…]+[\"”')\]]*\s+")
_SPEAKER = re.compile(r"^[A-Z][\w.]*(?: [A-Z][\w.]*){0,2}:\s+")


@dataclass
class Item:
    id: str
    kind: str
    text: str
    start: int
    end: int
    context: str
    ctx_start: int  # offset of the item inside context
    ctx_end: int


def _ranges(flags: list[bool], text: str) -> list[tuple[int, int]]:
    out = []
    i, n = 0, len(flags)
    while i < n:
        if flags[i] and text[i] not in "\n" + OBJ_CHAR:
            j = i
            while j < n and flags[j] and text[j] not in "\n" + OBJ_CHAR:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def _snap(text: str, s: int, e: int) -> tuple[int, int]:
    # Trim spaces/punctuation, then grow to whole words.
    while s < e and not _WORDCH.match(text[s]):
        s += 1
    while e > s and not _WORDCH.match(text[e - 1]):
        e -= 1
    if s >= e:
        return s, s
    while s > 0 and _WORDCH.match(text[s - 1]):
        s -= 1
    while e < len(text) and _WORDCH.match(text[e]):
        e += 1
    return s, e


def _context(text: str, s: int, e: int) -> tuple[str, int]:
    p_start = text.rfind("\n", 0, s) + 1
    p_end = text.find("\n", e)
    p_end = len(text) if p_end == -1 else p_end
    para = text[p_start:p_end]
    rs, re_ = s - p_start, e - p_start
    bounds = [0] + [m.end() for m in _SENT_END.finditer(para)] + [len(para)]
    c_start = max(b for b in bounds if b <= rs)
    c_end = min(b for b in bounds if b >= re_)
    sent = para[c_start:c_end]
    m = _SPEAKER.match(sent)
    if m and m.end() <= rs - c_start:
        c_start += m.end()
        sent = sent[m.end():]
    stripped = sent.rstrip()
    return stripped, p_start + c_start


def extract_items(note_id: str, text: str, runs: list[Run]) -> list[Item]:
    n = len(text)
    under = [False] * n
    high = [False] * n
    heading = [False] * n
    for r in runs:
        for i in range(r.start, min(r.end, n)):
            if r.underline:
                under[i] = True
            if r.highlight:
                high[i] = True
            if r.heading:
                heading[i] = True

    items: list[Item] = []
    seen: dict[tuple[str, str], int] = {}
    for kind, flags in (("vocab", high), ("mistake", under)):
        for rs, re_ in _ranges(flags, text):
            s, e = _snap(text, rs, re_)
            if s >= e or all(heading[s:e]) or not re.search(r"[A-Za-z]", text[s:e]):
                continue
            phrase = re.sub(r"\s+", " ", text[s:e]).strip()
            ctx, c0 = _context(text, s, e)
            key = (kind, phrase.lower())
            occ = seen.get(key, 0)
            seen[key] = occ + 1
            iid = hashlib.sha1(f"{note_id}|{kind}|{phrase.lower()}|{occ}".encode()).hexdigest()[:16]
            items.append(Item(iid, kind, phrase, s, e, ctx, s - c0, e - c0))
    items.sort(key=lambda it: it.start)
    return items
