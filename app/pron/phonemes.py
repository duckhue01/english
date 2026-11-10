"""ARPAbet (CMUdict) -> General American IPA, plus syllabification helpers."""

from __future__ import annotations

VOWELS = {
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
}

# Stress-dependent vowels first, then the rest.
_VOWEL_IPA = {
    "AA": "ɑ", "AE": "æ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ", "EH": "ɛ",
    "EY": "eɪ", "IH": "ɪ", "IY": "i", "OW": "oʊ", "OY": "ɔɪ", "UH": "ʊ",
    "UW": "u",
}

_CONS_IPA = {
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "F": "f", "G": "ɡ", "HH": "h",
    "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ", "P": "p",
    "R": "r", "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v", "W": "w",
    "Y": "j", "Z": "z", "ZH": "ʒ",
}

# Phonemes after which a following vowel gets a /j/ or /w/ glide when linking.
J_GLIDE_ENDINGS = {"IY", "EY", "AY", "OY", "IH"}
W_GLIDE_ENDINGS = {"UW", "OW", "AW", "UH"}

# Legal English onsets (as ARPAbet tuples) for maximal-onset syllabification.
_ONSETS_2 = {
    ("P", "L"), ("B", "L"), ("K", "L"), ("G", "L"), ("F", "L"), ("S", "L"),
    ("P", "R"), ("B", "R"), ("T", "R"), ("D", "R"), ("K", "R"), ("G", "R"),
    ("F", "R"), ("TH", "R"), ("SH", "R"),
    ("T", "W"), ("D", "W"), ("K", "W"), ("G", "W"), ("S", "W"), ("TH", "W"),
    ("S", "P"), ("S", "T"), ("S", "K"), ("S", "M"), ("S", "N"), ("S", "F"),
    ("P", "Y"), ("B", "Y"), ("K", "Y"), ("G", "Y"), ("M", "Y"), ("F", "Y"),
    ("V", "Y"), ("HH", "Y"), ("N", "Y"),
}
_ONSETS_3 = {
    ("S", "P", "L"), ("S", "P", "R"), ("S", "T", "R"), ("S", "K", "R"),
    ("S", "K", "W"), ("S", "K", "Y"), ("S", "P", "Y"),
}


def split_stress(ph: str) -> tuple[str, int | None]:
    """'AH0' -> ('AH', 0); 'T' -> ('T', None)."""
    if ph[-1].isdigit():
        return ph[:-1], int(ph[-1])
    return ph, None


def is_vowel(ph: str) -> bool:
    return split_stress(ph)[0] in VOWELS


def to_ipa(ph: str) -> str:
    base, stress = split_stress(ph)
    if base == "AH":
        return "ə" if stress == 0 else "ʌ"
    if base == "ER":
        return "ɚ" if stress == 0 else "ɝ"
    if base in _VOWEL_IPA:
        return _VOWEL_IPA[base]
    return _CONS_IPA.get(base, base.lower())


def _legal_onset(cluster: tuple[str, ...]) -> bool:
    if len(cluster) == 0:
        return True
    if len(cluster) == 1:
        return cluster[0] != "NG"
    if len(cluster) == 2:
        return cluster in _ONSETS_2
    if len(cluster) == 3:
        return cluster in _ONSETS_3
    return False


def syllabify(phones: list[str]) -> list[list[int]]:
    """Return syllables as lists of phone indices (maximal onset principle)."""
    nuclei = [i for i, p in enumerate(phones) if is_vowel(p)]
    if not nuclei:
        return [list(range(len(phones)))]
    bounds = [0]
    for a, b in zip(nuclei, nuclei[1:]):
        cons = [split_stress(phones[i])[0] for i in range(a + 1, b)]
        # Largest legal onset for the next syllable; the rest is coda.
        split = len(cons)
        for k in range(len(cons) + 1):
            if _legal_onset(tuple(cons[k:])):
                split = k
                break
        bounds.append(a + 1 + split)
    bounds.append(len(phones))
    return [list(range(bounds[i], bounds[i + 1])) for i in range(len(bounds) - 1)]
