"""Connected-speech analysis for General American English.

Given a word or phrase, produce per-word IPA with syllable stress, and mark
flap-T, glottal-T, optional /t/ drop after /n/, and linking between words.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

import pyphen

from .lexicon import THE_BEFORE_VOWEL, WEAK_FORMS, lookup
from .phonemes import (
    J_GLIDE_ENDINGS,
    W_GLIDE_ENDINGS,
    is_vowel,
    split_stress,
    syllabify,
    to_ipa,
)

_HYPH = pyphen.Pyphen(lang="en_US", left=1, right=1)
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)*|[^\sA-Za-z0-9]+")
_WORD_RE = re.compile(r"[A-Za-z0-9]")

_COALESCE = {"T": "tʃ", "D": "dʒ", "S": "ʃ", "Z": "ʒ"}
_HELD_STOP_PAIRS = {
    frozenset({"T", "D"}), frozenset({"P", "B"}), frozenset({"K", "G"}),
}


@dataclass
class Phone:
    arpa: str
    ipa: str
    stress: int | None
    feature: str | None = None  # flap | glottal | t_drop | coalesce


@dataclass
class Syllable:
    ipa: str
    stress: int  # 0 none, 1 primary, 2 secondary
    features: list[str] = field(default_factory=list)


@dataclass
class Link:
    type: str  # cv | glide_j | glide_w | vv | same | held_stop | coalesce
    label: str
    insert: str | None = None


@dataclass
class Word:
    text: str
    source: str
    weak: bool
    syllables: list[Syllable]
    ipa: str
    spelling: list[str] | None
    stressed_spelling: int | None
    link_next: Link | None = None
    is_word: bool = True


@dataclass
class Punct:
    text: str
    is_word: bool = False


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.replace("’", "'"))


def _choose_phones(word: str, next_word: str | None, phrase_final: bool):
    w = word.lower()
    if w in WEAK_FORMS and not phrase_final:
        if w == "the" and next_word:
            nxt, _ = lookup(next_word)
            if nxt and is_vowel(nxt[0]):
                return list(THE_BEFORE_VOWEL), "cmu", True
        return list(WEAK_FORMS[w]), "cmu", True
    phones, src = lookup(word)
    return list(phones), src, False


def analyze(text: str) -> list[dict]:
    toks = _tokens(text)
    items: list[Word | Punct] = []
    word_phones: list[list[Phone]] = []

    # 1. Lexical lookup.
    for i, tok in enumerate(toks):
        if not _WORD_RE.search(tok):
            items.append(Punct(tok))
            continue
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        next_word = nxt if nxt and _WORD_RE.search(nxt) else None
        phrase_final = next_word is None
        arpa, src, weak = _choose_phones(tok, next_word, phrase_final)
        phones = [Phone(p, to_ipa(p), split_stress(p)[1]) for p in arpa]
        items.append(Word(tok, src, weak, [], "", None, None))
        word_phones.append(phones)

    words = [it for it in items if isinstance(it, Word)]

    # Map each word to whether it is directly followed by another word.
    adjacent_next: list[bool] = []
    for idx, it in enumerate(items):
        if isinstance(it, Word):
            nxt = items[idx + 1] if idx + 1 < len(items) else None
            adjacent_next.append(isinstance(nxt, Word))

    # 2. Linking + coalescence across word boundaries.
    for wi, w in enumerate(words):
        if not adjacent_next[wi] or wi + 1 >= len(words):
            continue
        a_ph, b_ph = word_phones[wi], word_phones[wi + 1]
        if not a_ph or not b_ph:
            continue
        a, b = a_ph[-1], b_ph[0]
        a_base, b_base = split_stress(a.arpa)[0], split_stress(b.arpa)[0]
        a_v, b_v = is_vowel(a.arpa), is_vowel(b.arpa)
        if not a_v and b_v:
            w.link_next = Link("cv", "consonant → vowel")
        elif a_v and b_v:
            if a_base in J_GLIDE_ENDINGS:
                w.link_next = Link("glide_j", "vowel → vowel (/j/ glide)", "j")
            elif a_base in W_GLIDE_ENDINGS:
                w.link_next = Link("glide_w", "vowel → vowel (/w/ glide)", "w")
            else:
                w.link_next = Link("vv", "vowel → vowel")
        elif b_base == "Y" and a_base in _COALESCE:
            res = _COALESCE[a_base]
            a.ipa, a.feature = res, "coalesce"
            b.ipa, b.feature = "", "coalesce"
            w.link_next = Link("coalesce", f"/{to_ipa(a_base)}/ + /j/ → /{res}/")
        elif a_base == b_base:
            w.link_next = Link("same", "same consonant (say it once, longer)")
        elif frozenset({a_base, b_base}) in _HELD_STOP_PAIRS:
            w.link_next = Link("held_stop", "held stop (don't release the first)")

    # 3. Flap-T / glottal T / t-drop on the flattened phrase.
    flat: list[tuple[int, int]] = []  # (word index, phone index)
    breaks: set[int] = set()  # flat positions that start a new phrase
    for wi, phones in enumerate(word_phones):
        if wi == 0 or not adjacent_next[wi - 1]:
            breaks.add(len(flat))
        for pi in range(len(phones)):
            flat.append((wi, pi))

    def ph_at(k: int) -> Phone:
        wi, pi = flat[k]
        return word_phones[wi][pi]

    for k, (wi, pi) in enumerate(flat):
        cur = ph_at(k)
        base = split_stress(cur.arpa)[0]
        if base not in {"T", "D"} or cur.feature:
            continue
        if k == 0 or k in breaks or k + 1 >= len(flat) or (k + 1) in breaks:
            continue
        prev, nxt = ph_at(k - 1), ph_at(k + 1)
        prev_base = split_stress(prev.arpa)[0]
        nxt_wi, nxt_pi = flat[k + 1]
        word_len = len(word_phones[wi])
        word_initial = pi == 0
        crosses = nxt_wi != wi

        # Glottal T: button, mountain, certain (T + unstressed AH + N at word end).
        if (
            base == "T" and not crosses
            and pi + 2 == word_len - 1
            and split_stress(word_phones[wi][pi + 1].arpa) == ("AH", 0)
            and split_stress(word_phones[wi][pi + 2].arpa)[0] == "N"
            and (is_vowel(prev.arpa) or prev_base in {"R", "N"})
        ):
            cur.ipa, cur.feature = "ʔ", "glottal"
            continue

        if not is_vowel(nxt.arpa):
            continue
        nxt_stress = split_stress(nxt.arpa)[1]

        # Optional /t/ drop: twenty, internet, center (N + T + unstressed vowel).
        if base == "T" and prev_base == "N" and not crosses and nxt_stress == 0 and not word_initial:
            cur.feature = "t_drop"
            continue

        if not (is_vowel(prev.arpa) or prev_base == "R"):
            continue
        if word_initial and not words[wi].weak:
            continue  # "a top" keeps its /t/
        if crosses or nxt_stress == 0 or (word_initial and words[wi].weak):
            cur.ipa, cur.feature = "ɾ", "flap"

    # 4. Build syllables, IPA strings, spelling syllables.
    for wi, w in enumerate(words):
        phones = word_phones[wi]
        if not phones:
            w.ipa = "?"
            continue
        sylls = syllabify([p.arpa for p in phones])
        multi = len(sylls) > 1
        out_sylls: list[Syllable] = []
        for idxs in sylls:
            stress = 0
            feats: list[str] = []
            parts = []
            for i in idxs:
                p = phones[i]
                if p.stress:
                    stress = p.stress
                if p.feature:
                    feats.append(p.feature)
                parts.append(f"({p.ipa})" if p.feature == "t_drop" else p.ipa)
            if w.weak:
                stress = 0
            out_sylls.append(Syllable("".join(parts), stress, feats))
        w.syllables = out_sylls
        marks = {1: "ˈ", 2: "ˌ", 0: ""}
        w.ipa = ".".join(
            (marks[s.stress] if multi else "") + s.ipa for s in out_sylls
        ).replace(".ˈ", "ˈ").replace(".ˌ", "ˌ")
        spelling = _HYPH.inserted(w.text, hyphen="\u00b7").split("\u00b7")
        if len(spelling) == len(out_sylls) and multi:
            w.spelling = spelling
            primary = [i for i, s in enumerate(out_sylls) if s.stress == 1]
            w.stressed_spelling = primary[0] if primary else None

    return [asdict(it) for it in items]


def phrase_ipa(text: str) -> str:
    """Compact connected-speech transcription, e.g. 'ɡɛɾ‿ɪt'."""
    out = []
    for it in analyze(text):
        if not it["is_word"]:
            continue
        s = it["ipa"]
        link = it.get("link_next")
        if link:
            s += "‿" + (link["insert"] or "") if link["insert"] else "‿"
        else:
            s += " "
        out.append(s)
    return "".join(out).strip().replace("‿ ", "‿")
