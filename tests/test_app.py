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


def test_notes_sorting_and_items_filter(tmp_path, monkeypatch):
    from app import db
    import app.main
    from app.main import list_items, list_notes

    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)

    db.init()
    with db.connect() as con:
        con.execute("INSERT OR REPLACE INTO notes (id, folder, title, text, runs, synced_at) VALUES ('n10', 'Test', '10 Tenth Note', '', '[]', '2026-01-01')")
        con.execute("INSERT OR REPLACE INTO notes (id, folder, title, text, runs, synced_at) VALUES ('n2', 'Test', '2 Second Note', '', '[]', '2026-01-01')")
        con.execute("INSERT OR REPLACE INTO notes (id, folder, title, text, runs, synced_at) VALUES ('nq', 'Test', 'Questions & Answers', '', '[]', '2026-01-01')")
        con.execute("INSERT OR REPLACE INTO items (id, note_id, folder, kind, text, context, ctx_start, ctx_end, position, active, created_at, updated_at) VALUES ('i1', 'n2', 'Test', 'vocab', 'word', 'a word', 2, 6, 0, 1, '2026-01-01', '2026-01-01')")
        con.execute("INSERT OR REPLACE INTO items (id, note_id, folder, kind, text, context, ctx_start, ctx_end, position, active, created_at, updated_at) VALUES ('i2', 'n10', 'Test', 'vocab', 'another', 'another word', 0, 7, 0, 1, '2026-01-01', '2026-01-01')")

    notes = list_notes(folder="Test")
    titles = [n["title"] for n in notes]
    assert titles == ["2 Second Note", "10 Tenth Note", "Questions & Answers"]

    items_n2 = list_items(note_id="n2")
    assert len(items_n2) == 1
    assert items_n2[0]["text"] == "word"
