from __future__ import annotations

from app.extract import extract_items
from app.notes_source import html_to_runs
from app.pron.engine import analyze, phrase_ipa


def test_flap_and_glottal():
    assert phrase_ipa("water") == "ˈwɔ.ɾɚ"
    assert phrase_ipa("get it") == "ɡɛɾ‿ɪt"
    assert phrase_ipa("button") == "ˈbʌ.ʔən"
    assert phrase_ipa("twenty") == "ˈtwɛn.(t)i"


def test_stress_and_syllables():
    tokens = analyze("pronunciation")
    w = tokens[0]
    assert w["ipa"] == "proʊˌnʌn.siˈeɪ.ʃən"
    assert w["spelling"] == ["pro", "nun", "ci", "a", "tion"]
    assert w["stressed_spelling"] == 3


def test_linking_and_coalescence():
    assert phrase_ipa("turn off") == "tɝn‿ɔf"
    assert phrase_ipa("go away") == "ɡoʊ‿wəˈweɪ"
    assert phrase_ipa("see it") == "si‿jɪt"
    assert phrase_ipa("did you") == "dɪdʒ‿u"
    assert phrase_ipa("bad day") == "bæd‿deɪ"


def test_extract_underline_and_bold():
    html = (
        "<h1>2 Specialization</h1>"
        "<div>Remember, economics is the <u>study of </u><b><u>sca</u></b><u>rcity and choices</u>. "
        "We also learn <b>comparative</b> advantage and oppor<b>tu</b>nity cost.</div>"
    )
    text, runs = html_to_runs(html)
    items = extract_items("note-1", text, runs)
    mistakes = [i for i in items if i.kind == "mistake"]
    vocabs = [i for i in items if i.kind == "vocab"]

    assert len(mistakes) == 1
    assert mistakes[0].text == "study of scarcity and choices"
    assert "economics is the study of scarcity and choices." in mistakes[0].context

    assert len(vocabs) == 1
    assert vocabs[0].text == "comparative"
