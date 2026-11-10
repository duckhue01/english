"""Turn formatted note text into learning items.

* bold       -> kind "vocab"   (new vocabulary)
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


def _whole_word_bold_ranges(bold: list[bool], heading: list[bool], text: str) -> list[tuple[int, int]]:
    """Extract only whole-word bold spans (ignoring single-syllable stress bolds and headings)."""
    n = len(text)
    whole = [False] * n
    for rs, re_ in _ranges(bold, text):
        bs, be = rs, re_
        while bs < be and not _WORDCH.match(text[bs]):
            bs += 1
        while be > bs and not _WORDCH.match(text[be - 1]):
            be -= 1
        if bs >= be or all(heading[bs:be]):
            continue
        s, e = _snap(text, bs, be)
        # Must cover the full word(s), not just a stressed syllable inside a word,
        # and not be a label ending with ':' or a standalone multi-word heading line.
        if bs != s or be != e or text[be : be + 1] == ":":
            continue
        ls = text.rfind("\n", 0, bs) + 1
        le = text.find("\n", be)
        le = n if le == -1 else le
        if text[ls:le].strip() == text[rs:re_].strip() and len(text[bs:be].split()) >= 3:
            continue
        for i in range(bs, be):
            whole[i] = True

    # Bridge horizontal whitespace between adjacent whole-word bold spans (e.g. <b>dairy</b> <b>farmer</b>).
    merged: list[tuple[int, int]] = []
    for rs, re_ in _ranges(whole, text):
        if merged and text[merged[-1][1] : rs].strip() == "" and "\n" not in text[merged[-1][1] : rs]:
            merged[-1] = (merged[-1][0], re_)
        else:
            merged.append((rs, re_))
    return merged


def extract_items(note_id: str, text: str, runs: list[Run]) -> list[Item]:
    n = len(text)
    under = [False] * n
    bold = [False] * n
    heading = [False] * n
    for r in runs:
        for i in range(r.start, min(r.end, n)):
            if r.underline:
                under[i] = True
            if r.bold:
                bold[i] = True
            if r.heading:
                heading[i] = True

    items: list[Item] = []
    seen: dict[tuple[str, str], int] = {}
    kind_ranges = (
        ("vocab", _whole_word_bold_ranges(bold, heading, text), False),
        ("mistake", _ranges(under, text), True),
    )
    for kind, raw_ranges, snap_words in kind_ranges:
        for rs, re_ in raw_ranges:
            s, e = _snap(text, rs, re_) if snap_words else (rs, re_)
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
