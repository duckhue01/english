# English Notes Coach

A local macOS web app that syncs selected **Apple Notes** folders, extracts your marked words and phrases, and provides **General American (GA)** pronunciation analysis—including IPA, syllable stress, connected-speech linking, and flap-T rules.

Apple Notes is treated as **read-only**; your practice progress and notes are stored locally in SQLite and preserved across re-syncs.

---

## Marking Syntax in Apple Notes

Format text directly in Apple Notes while studying or reading transcripts:

| Formatting in Apple Notes | Extracted As | Purpose |
| :--- | :--- | :--- |
| <mark>**Highlight**</mark> | **Vocabulary** (`vocab`) | New words or idioms to learn |
| <u>**Underline**</u> | **Pronunciation Mistake** (`mistake`) | Words/phrases to practice and track (`new` → `practicing` → `fixed`) |

> **Note:** If you only underline or highlight part of a word (e.g., `re`<u>`fri`</u>`gerators`), the extractor automatically snaps the selection to the full word (`refrigerators`) and captures the surrounding sentence as context.

---

## Features

- **Multi-Folder Sync**: Add any number of Apple Notes folders (e.g., `Economic Crash Course`, `English`) and sync them on demand.
- **General American Pronunciation Engine**:
  - **IPA & Syllable Stress**: Uses CMUdict with a neural `g2p_en` fallback for out-of-vocabulary words. Splits syllables via the maximal-onset principle and highlights primary (`ˈ`) and secondary (`ˌ`) stress (e.g., `pro·nun·ci·A·tion` → `/proʊˌnʌn.siˈeɪ.ʃən/`).
  - **Flap-T (`ɾ`)**: Detects intervocalic and post-`/r/` `/t, d/` within words and across word boundaries (`water` → `/ˈwɔ.ɾɚ/`, `get it` → `/ɡɛɾ‿ɪt/`).
  - **Glottal-T (`ʔ`) & Optional `/t/` Drop (`(t)`)**: Marks glottal stops before syllabic `/n/` (`button` → `/ˈbʌ.ʔən/`) and casual `/nt/` reductions (`twenty` → `/ˈtwɛn.(t)i/`).
  - **Connected-Speech Linking (`‿`)**:
    - Consonant → Vowel (`turn‿off`)
    - Vowel → Vowel with `/j/` or `/w/` glides (`see‿ʲit`, `go‿ʷaway`)
    - Geminate / Held stops (`bad‿day`)
    - Coalescence (`did you` → `/dɪdʒ‿u/`)
  - **Weak Forms**: Reduces common function words (`to`, `of`, `and`, `for`, `the`) in connected phrases.
- **Mistake Tracker**: Filter mistakes by folder, status (`new`, `practicing`, `fixed`), or search query, and attach personal practice notes.
- **Interactive Note Reader**: Read your synced notes with highlights and underlines preserved. Click any marked span—or highlight any arbitrary text with your cursor—to inspect its pronunciation and listen at normal (`🔊`) or slow (`🐢`) speed.
- **Free-Text Analyzer**: Paste any English sentence to get a full connected-speech breakdown.

---

## Quick Start

### 1. Run the App

```bash
./run.sh
```

Then open **http://127.0.0.1:8000** in your browser.

`./run.sh` builds the React frontend into `frontend/dist` (if not already built) and starts the FastAPI server via Uvicorn on port `8000`.

### 2. Enable Highlight Detection (Full Disk Access)

Apple's AppleScript bridge exposes `<u>` (underline) but strips text highlights. To read **highlights** (`vocab`), the backend reads a read-only temporary snapshot of `~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite`.

1. Open **System Settings → Privacy & Security → Full Disk Access**.
2. Toggle access **ON** for the terminal or IDE running `./run.sh` (e.g., **Terminal**, **iTerm**, or **Orca**).
3. Restart the terminal/IDE and run `./run.sh` again.

Without Full Disk Access, the app automatically falls back to AppleScript (underlines work; highlights are skipped).

---

## Development

### Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI routes & static SPA serving
│   │   ├── notes_source.py  # NoteStore.sqlite protobuf reader + AppleScript fallback
│   │   ├── extract.py       # Span extraction, word snapping & sentence context
│   │   ├── sync.py          # Folder sync service
│   │   ├── db.py            # SQLite schema & connection helper
│   │   └── pron/
│   │       ├── phonemes.py  # ARPAbet → GA IPA & maximal-onset syllabifier
│   │       ├── lexicon.py   # CMUdict + g2p_en lookup & weak forms
│   │       └── engine.py    # Flap-T, glottal-T, linking & coalescence rules
│   └── tests/
│       └── test_app.py      # Pytest suite
├── frontend/
│   └── src/
│       ├── api.ts           # Typed API client & Web Speech synthesis helper
│       ├── components/      # Pronunciation & ItemCard components
│       └── pages/           # Folders, Vocabulary/Mistakes, Notes, Analyzer
└── run.sh                   # Single-command launcher
```

### Run Backend & Frontend Separately (Hot Reload)

```bash
# Terminal 1 – FastAPI backend on :8000
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 2 – Vite dev server on :5173 (proxies /api -> :8000)
cd frontend && npm run dev
```

### Run Tests

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_app.py -v
```
