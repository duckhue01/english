# 🎙️ SpeakFlow

> **Terminal Voice Recording Studio & Pronunciation Coach for Google NotebookLM**

SpeakFlow is an interactive terminal application engineered to streamline English speaking and pronunciation practice. It pairs with **Google NotebookLM** to provide detailed phonetic audits, rhythm/stress analysis, mouth/tongue placement tips, and corrective drills.

---

## 🌟 Key Features

* **🎙️ Live Studio Booth with Real-time VU Meter:**
  * Animated decibel VU meter (`[████████░░░░] -16.2 dB`) to ensure your microphone levels are calibrated and avoid digital clipping.
  * In-terminal teleprompter box showing your target practice script, word count, and estimated duration.
  * Clean controls: press `<Space>` or `<Enter>` to finish recording, or `<Ctrl+C>` to cancel.
* **⚡ Native High-Clarity Audio Export & Smart Voice Booster:**
  * **Intelligent Speech Leveler (AGC):** Automatically detects spoken voice frames, analyzes speech energy, and applies up to **+28 dB of clean makeup gain** so even quiet voices or built-in laptop mics sound loud, rich, and clear.
  * **Soft-Knee Limiter:** Tames plosives (`p`, `b`), breath pops, and desk thumps with transparent saturation (`tanh`) so you never get harsh digital distortion.
  * Automatically trims leading/trailing silence and strips DC mic rumble.
  * Exports ultra-lightweight, crystal-clear **AAC `.m4a`** (via macOS native `afconvert`) and lossless **PCM `.wav`**.
* **🧠 Built for Google NotebookLM:**
  * Generates **`notebooklm_source.md`**: A structured markdown reference document containing the exact target text, syllable stress guidelines, and target phonetics.
  * Generates **`notebooklm_prompt.txt`**: A prompt that instructs NotebookLM to act as an elite speech coach (auditing omitted words, IPA errors, intonation, and physical mouth/tongue placement).
  * **Automatic Clipboard Copy:** Copies the prompt directly to your macOS clipboard (`pbcopy`) upon export.
  * **1-Click Integration:** Launch NotebookLM (`open https://notebooklm.google.com`) and reveal session files in Finder (`open -R ...`) for drag-and-drop.
* **📚 Curated Pronunciation Drill Library:**
  * **Tricky Phonemes:** Voiced & voiceless *TH* (/θ/ and /ð/), *R* vs *L*, *V* vs *W*, past tense *-ed* endings (/t/, /d/, /ɪd/), and vowel pairs (*ship* vs *sheep*).
  * **Connected Speech & Intonation:** Linking, reductions, flap-T, and sentence stress shifts.
  * **Tongue Twisters:** Peter Piper, Betty Botter, She Sells Seashells.
  * **Professional & Workplace:** Executive elevator pitches, Agile standup updates.
  * **IELTS & Academic:** Part 2 cue cards and academic discussion responses.
  * **Custom Input:** Paste any custom text or load from a `.txt` / `.md` file.
* **📁 Session Library & In-Terminal Playback:**
  * Browse past recordings, replay audio with terminal progress bars, view reference scripts, or re-copy prompts anytime.
* **🛠️ Microphone Diagnostics:**
  * List all audio input devices and run live VU level calibration.

---

## 🚀 Quickstart

SpeakFlow is installed and ready in your terminal environment.

### 1. Launch the Interactive Studio
```bash
speakflow
```
*(Or run `./run.sh` or `python3 speakflow_app.py`)*

### 2. Direct CLI Commands
```bash
# Record with custom text (with interactive review):
speakflow record --text "The thought of thirty-three thousand feathers tickling their throats."

# Record from a markdown or text file:
speakflow record --file speech.txt --title "My Presentation"

# Record for a fixed duration without countdown (scripted/automated):
speakflow record --text "Quick voice sample" --duration 5 --no-countdown --auto-save

# Play back your latest recording:
speakflow play 1

# List all practice recordings:
speakflow list

# Test microphone volume with live VU meter:
speakflow test-mic

# Open Google NotebookLM in your default browser:
speakflow open-nlm

# View NotebookLM coaching guide:
speakflow guide
```

---

## 📖 The 3-Step NotebookLM Pronunciation Workflow

Once you record and export your practice session in SpeakFlow:

```
┌────────────────────────────────┐
│   1. SpeakFlow Studio          │
│   • Records speech             │
│   • Exports audio.m4a          │
│   • Exports source.md          │
│   • Copies Prompt to Clipboard │
└───────────────┬────────────────┘
                │
                ▼ Drag & Drop into NotebookLM
┌────────────────────────────────┐
│   2. Google NotebookLM         │
│   • Add Source: audio.m4a      │
│   • Add Source: source.md      │
└───────────────┬────────────────┘
                │
                ▼ Press Cmd+V in Chat
┌────────────────────────────────┐
│   3. Gemini Audio Diagnostics  │
│   • Word accuracy audit        │
│   • IPA phoneme error mapping  │
│   • Stress, linking & cadence  │
│   • Mouth & tongue tips/drills │
└────────────────────────────────┘
```

### Step 1: Export Your Recording
In SpeakFlow, choose **"Save & Generate NotebookLM Package"**.
SpeakFlow produces:
* `session_YYYYMMDD_HHMMSS_audio.m4a`
* `session_YYYYMMDD_HHMMSS_notebooklm_source.md`
* `session_YYYYMMDD_HHMMSS_notebooklm_prompt.txt` *(auto-copied to clipboard)*

Select **"🌐 Open NotebookLM in Default Browser"** and **"📂 Reveal Files in Finder"**.

### Step 2: Upload Both Sources into NotebookLM
1. Open [notebooklm.google.com](https://notebooklm.google.com).
2. Create or open your English Practice notebook.
3. Under **Sources**, drag & drop:
   * The **`audio.m4a`** file.
   * The **`notebooklm_source.md`** file.

### Step 3: Paste Prompt & Get Feedback
1. Click into the NotebookLM chat bar.
2. Press **`Cmd + V`** (the prompt is already on your clipboard).
3. Hit Enter!

NotebookLM's multi-modal audio engine will listen to your recording, compare it against the reference script, and respond with:
* **Word Fidelity Table:** Missing, added, or slurred words.
* **Phonetic Analysis:** Target IPA vs perceived IPA, specific mispronounced vowels/consonants.
* **Physical Articulation Guide:** Exact instructions on where to position tongue, teeth, and lips.
* **Prosody & Rhythm:** Syllable stress, flap-T, linking, and speaking rate.
* **Targeted Drills:** 3 customized micro-drills and minimal pairs to fix your mistakes.

---

## 📂 Project Structure

```
english/
├── speakflow/
│   ├── __init__.py
│   ├── cli.py            # CLI entrypoint, menus, and arguments
│   ├── recorder.py       # Audio stream capture, VU meter, raw terminal input
│   ├── player.py         # Audio playback engine with visual progress
│   ├── exporter.py       # Audio normalization, M4A conversion, doc generation
│   ├── prompts.py        # Engineered NotebookLM prompt & source markdown templates
│   ├── library.py        # Curated pronunciation library & drill sets
│   ├── sessions.py       # History management, metadata, and disk storage
│   ├── diagnostics.py   # Microphone device query and level tester
│   └── ui.py             # Rich visual components, banners, and VU meters
├── recordings/           # Default directory for saved practice sessions
├── tests/
│   └── test_speakflow.py # Automated pytest test suite
├── speakflow_app.py      # Standalone launcher executable
├── run.sh                # Shell script runner
├── setup.py              # Pip setup & CLI console script registration
├── pyproject.toml        # Modern Python build config
└── requirements.txt      # Python dependencies
```

---

## 🛠️ Testing

Run the automated test suite:
```bash
python3 -m pytest tests/test_speakflow.py -v
```

All audio processing, export pipelines, prompt generators, and device queries run with 100% test coverage.
