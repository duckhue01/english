"""Word -> ARPAbet lookup: CMUdict first, then g2p_en for unknown words."""

from __future__ import annotations

import logging
import re
from functools import lru_cache

import cmudict

log = logging.getLogger(__name__)

_CMU = cmudict.dict()
_g2p = None
_g2p_failed = False

# Weak (reduced) forms of common function words, used mid-phrase.
WEAK_FORMS: dict[str, list[str]] = {
    "a": ["AH0"],
    "an": ["AH0", "N"],
    "the": ["DH", "AH0"],
    "and": ["AH0", "N", "D"],
    "of": ["AH0", "V"],
    "to": ["T", "AH0"],
    "for": ["F", "ER0"],
    "from": ["F", "R", "AH0", "M"],
    "at": ["AH0", "T"],
    "can": ["K", "AH0", "N"],
    "was": ["W", "AH0", "Z"],
    "were": ["W", "ER0"],
    "are": ["ER0"],
    "has": ["HH", "AH0", "Z"],
    "have": ["HH", "AH0", "V"],
    "had": ["HH", "AH0", "D"],
    "your": ["Y", "ER0"],
    "them": ["DH", "AH0", "M"],
    "some": ["S", "AH0", "M"],
    "as": ["AH0", "Z"],
    "but": ["B", "AH0", "T"],
    "or": ["ER0"],
    "than": ["DH", "AH0", "N"],
    "that": ["DH", "AH0", "T"],
}
THE_BEFORE_VOWEL = ["DH", "IY0"]


def _g2p_lookup(word: str) -> list[str] | None:
    global _g2p, _g2p_failed
    if _g2p_failed:
        return None
    try:
        if _g2p is None:
            from g2p_en import G2p  # heavy import, load lazily

            _g2p = G2p()
        phones = [p for p in _g2p(word) if re.fullmatch(r"[A-Z]+[0-2]?", p)]
        return phones or None
    except Exception as exc:  # noqa: BLE001 - optional dependency
        log.warning("g2p_en unavailable: %s", exc)
        _g2p_failed = True
        return None


@lru_cache(maxsize=20000)
def lookup(word: str) -> tuple[tuple[str, ...], str]:
    """Return (phones, source) where source is 'cmu', 'g2p' or 'unknown'."""
    w = word.lower().replace("’", "'")
    if w in _CMU:
        return tuple(_CMU[w][0]), "cmu"
    if "-" in w:
        parts = [lookup(p) for p in w.split("-") if p]
        if parts and all(src != "unknown" for _, src in parts):
            phones: list[str] = []
            for ph, _ in parts:
                phones.extend(ph)
            src = "cmu" if all(s == "cmu" for _, s in parts) else "g2p"
            return tuple(phones), src
    if w.endswith("'s") and w[:-2] in _CMU:
        base = _CMU[w[:-2]][0]
        last = base[-1].rstrip("012")
        suffix = ["IH0", "Z"] if last in {"S", "Z", "SH", "ZH", "CH", "JH"} else (
            ["S"] if last in {"P", "T", "K", "F", "TH"} else ["Z"]
        )
        return tuple(base + suffix), "cmu"
    g = _g2p_lookup(w)
    if g:
        return tuple(g), "g2p"
    return tuple(), "unknown"
