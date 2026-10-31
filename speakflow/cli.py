"""
Main CLI Interface and Interactive Terminal Application for SpeakFlow.
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import questionary
from questionary import Choice
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

from speakflow import __version__
from speakflow.ui import make_header, render_script_panel, render_phrase_teleprompter
from speakflow.library import PRACTICE_LIBRARY, get_categories, get_items_by_category
from speakflow.recorder import record_session
from speakflow.player import play_audio_file, play_audio_array, speak_phrase
from speakflow.analyzer import (
    analyze_phrase_phonetics,
    analyze_speech_acoustics,
    render_phrase_coaching_card,
    render_realtime_feedback_card,
)
from speakflow.exporter import (
    export_session,
    copy_to_clipboard,
    open_browser,
    reveal_in_finder,
)
from speakflow.sessions import (
    get_all_sessions,
    display_sessions_table,
    delete_session,
)
from speakflow.diagnostics import (
    list_microphones,
    display_microphones_table,
    test_microphone_level,
    get_macos_input_volume,
    set_macos_input_volume,
    run_quick_voice_check,
)

console = Console()

# Global state
ACTIVE_DEVICE_INDEX: Optional[int] = None
WITH_COUNTDOWN: bool = True
VOICE_BOOST_MODE: str = "auto"


def show_notebooklm_guide():
    """Display an in-depth visual guide on pairing SpeakFlow with Google NotebookLM."""
    guide_md = """
# 🧠 Maximizing Pronunciation Feedback with Google NotebookLM

SpeakFlow and Google NotebookLM create a powerful speech-coaching loop:

### 1. How It Works
* **Audio Source:** NotebookLM accepts audio (`.m4a`, `.wav`, `.mp3`) and transcribes the speech.
* **Text Source:** NotebookLM accepts markdown/text (`.md`) as the ground-truth Reference Script.
* **Gemini Multi-Modal Engine:** By analyzing the audio against the script, NotebookLM detects:
  - Mispronounced vowels and consonants (e.g. /θ/ vs /s/, /r/ vs /l/, dropped -ed/-s).
  - Pausing, speech rhythm, and syllable stress.
  - Sentence-level melody and intonation contours.

### 2. Step-by-Step Workflow
1. **Record:** Pick a script or paste your own passage in SpeakFlow and speak into your mic.
2. **Export:** SpeakFlow automatically generates:
   - High-clarity **`audio.m4a`**
   - Paired context file **`notebooklm_source.md`**
   - Specialized diagnostic prompt (auto-copied to your clipboard).
3. **Upload to NotebookLM:**
   - Go to [notebooklm.google.com](https://notebooklm.google.com).
   - Create a notebook (e.g., *"My English Speaking Lab"*).
   - Click **Add Source** -> Drag & drop the `.m4a` and `.md` files.
4. **Run Analysis:**
   - In the chat box, simply press **`Cmd + V`** to paste the generated prompt and hit Enter.
   - NotebookLM will generate a word-by-word audit, IPA error breakdown, and physical tongue/mouth tips!
"""
    console.print(Panel(Markdown(guide_md), title="[bold cyan]NotebookLM Workflow Guide[/bold cyan]", border_style="cyan", padding=(1, 2)))
    questionary.press_any_key_to_continue("Press any key to return to menu...").ask()


def select_practice_text() -> Optional[Dict[str, Any]]:
    """Prompt user to choose or input a practice text."""
    choice = questionary.select(
        "Select Practice Text Source:",
        choices=[
            Choice("📚 Choose from Curated Pronunciation Library", value="library"),
            Choice("✏️  Type or Paste Custom Passage", value="custom"),
            Choice("📄 Load from a Text / Markdown File", value="file"),
            Choice("🔙 Back to Main Menu", value="back"),
        ],
    ).ask()

    if not choice or choice == "back":
        return None

    if choice == "library":
        categories = get_categories()
        cat_choices = [Choice(f"📁 {cat}", value=cat) for cat in categories]
        cat_choices.append(Choice("🔙 Back", value="back"))

        selected_cat = questionary.select("Select Category:", choices=cat_choices).ask()
        if not selected_cat or selected_cat == "back":
            return None

        items = get_items_by_category(selected_cat)
        item_choices = [
            Choice(f"[{item['difficulty']}] {item['title']}", value=item)
            for item in items
        ]
        item_choices.append(Choice("🔙 Back", value="back"))

        selected_item = questionary.select("Select Drill:", choices=item_choices).ask()
        if not selected_item or selected_item == "back":
            return None

        return selected_item

    elif choice == "custom":
        title = questionary.text("Enter a title for this session:", default="Custom Speaking Practice").ask()
        if not title:
            return None

        console.print("[dim]Paste or type your target text below. Press Enter when finished:[/dim]")
        text = questionary.text("Practice Script:").ask()
        if not text or not text.strip():
            console.print("[yellow]Empty script. Cancelled.[/yellow]")
            return None

        notes = questionary.text("Specific phonetic or focus notes (optional):", default="").ask()
        return {
            "id": f"custom_{int(datetime.now().timestamp())}",
            "title": title.strip(),
            "text": text.strip(),
            "category": "Custom Practice",
            "difficulty": "Personal",
            "focus": notes.strip(),
        }

    elif choice == "file":
        filepath = questionary.path("Enter path to text or markdown file:").ask()
        if not filepath or not os.path.exists(filepath):
            console.print(f"[red]File not found: {filepath}[/red]")
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            
            title = Path(filepath).stem.replace("_", " ").title()
            return {
                "id": f"file_{int(datetime.now().timestamp())}",
                "title": f"File: {title}",
                "text": content,
                "category": "External Document",
                "difficulty": "Custom",
                "focus": f"Loaded from {filepath}",
            }
        except Exception as e:
            console.print(f"[red]Failed to read file: {e}[/red]")
            return None

    return None


def handle_phrase_coach_flow(initial_phrase: Optional[str] = None):
    """
    Dedicated interactive coach for phrases.
    Provides instant IPA breakdown, syllable stress, mouth/tongue tips,
    and real-time feedback on pacing, rhythm, and acoustic flow.
    """
    current_phrase = initial_phrase

    while True:
        if not current_phrase:
            if not sys.stdin.isatty():
                current_phrase = "Study of scarcity and choices"
            else:
                entered = questionary.text(
                    "Enter a phrase or sentence to practice:",
                    default="Study of scarcity and choices",
                ).ask()
                if not entered or not entered.strip():
                    break
                current_phrase = entered.strip()

        # Phonetic analysis
        analysis = analyze_phrase_phonetics(current_phrase)

        # Show coaching card
        console.clear()
        console.print(make_header())
        card = render_phrase_coaching_card(analysis)
        console.print(card)

        action = questionary.select(
            f"Phrase Coach: \"{current_phrase}\"",
            choices=[
                Choice("🎙️  Record Voice & Get Real-Time Feedback", value="record"),
                Choice("🗣️  Listen to Native Audio Model (Reference)", value="listen_native"),
                Choice("✏️  Practice a Different Phrase", value="change_phrase"),
                Choice("🏠 Return to Main Menu", value="back"),
            ],
        ).ask()

        if action == "listen_native":
            speak_phrase(current_phrase, rate=140)
            questionary.press_any_key_to_continue().ask()
            continue
        elif action == "change_phrase":
            current_phrase = None
            continue
        elif action == "back" or not action:
            break

        # Recording loop
        teleprompter = render_phrase_teleprompter(
            phrase=current_phrase,
            full_ipa=analysis["full_ipa"],
            word_cards=analysis["word_cards"],
            connected_cues=analysis["connected_cues"],
        )

        while True:
            record_res = record_session(
                title=f"Phrase: {current_phrase}",
                text=current_phrase,
                category="Phrase Lab",
                difficulty="Focused Drill",
                focus_notes=f"IPA: /{analysis['full_ipa']}/",
                device_index=ACTIVE_DEVICE_INDEX,
                with_countdown=WITH_COUNTDOWN,
                custom_panel=teleprompter,
            )

            if record_res is None:
                break

            audio_data, samplerate = record_res

            # Acoustic and speech rhythm feedback
            acoustics = analyze_speech_acoustics(audio_data, samplerate, current_phrase)

            # Show feedback loop
            fb_action = None
            while fb_action not in ("save", "rerecord", "done"):
                console.clear()
                console.print(make_header())
                feedback_panel = render_realtime_feedback_card(analysis, acoustics)
                console.print(feedback_panel)

                fb_action = questionary.select(
                    "Real-Time Pronunciation Options:",
                    choices=[
                        Choice("🔊 Play Back Your Recording", value="play_user"),
                        Choice("🗣️  Listen to Native Reference (Compare)", value="play_native"),
                        Choice("🔄 Try Again (Re-record with Instant Audit)", value="rerecord"),
                        Choice("💾 Save & Export Package for NotebookLM", value="save"),
                        Choice("🔙 Back to Phrase Lab", value="done"),
                    ],
                ).ask()

                if fb_action == "play_user":
                    play_audio_array(audio_data, samplerate, title=f"Your Recording: {current_phrase}")
                    questionary.press_any_key_to_continue().ask()
                elif fb_action == "play_native":
                    speak_phrase(current_phrase, rate=140)
                    questionary.press_any_key_to_continue().ask()
                elif fb_action == "save":
                    session_id = f"phrase_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    export_result = export_session(
                        audio_data=audio_data,
                        samplerate=samplerate,
                        session_id=session_id,
                        title=f"Phrase: {current_phrase}",
                        text=current_phrase,
                        category="Phrase Pronunciation Lab",
                        difficulty="Drill",
                        phonetic_focus=(
                            f"Target IPA: /{analysis['full_ipa']}/\n"
                            + "\n".join(f"- {c['word']} (/{c['ipa']}/): {c['tips'][0]}" for c in analysis["word_cards"] if c["tips"])
                        ),
                        auto_copy_prompt=True,
                        boost_mode=VOICE_BOOST_MODE,
                    )
                    handle_post_export(export_result)
                    break

            if fb_action != "rerecord":
                break


def handle_record_flow(
    practice_item: Dict[str, Any],
    max_duration: Optional[float] = None,
    no_countdown: bool = False,
    auto_save: bool = False,
    boost_mode: Optional[str] = None,
):
    """Execute the recording, reviewing, and export pipeline."""
    title = practice_item["title"]
    text = practice_item["text"]
    category = practice_item.get("category", "General")
    difficulty = practice_item.get("difficulty", "Intermediate")
    focus = practice_item.get("focus", "")
    active_boost = boost_mode if boost_mode is not None else VOICE_BOOST_MODE

    # Display preview
    if sys.stdout.isatty():
        console.clear()
        console.print(make_header())
    preview_panel = render_script_panel(
        title=title,
        text=text,
        category=category,
        difficulty=difficulty,
        focus_notes=focus,
    )
    console.print(preview_panel)

    if not auto_save and sys.stdin.isatty():
        start_confirm = questionary.confirm("Ready to start recording booth?", default=True).ask()
        if not start_confirm:
            return

    with_countdown = False if no_countdown else WITH_COUNTDOWN

    # Recording loop (supports re-recording)
    while True:
        record_res = record_session(
            title=title,
            text=text,
            category=category,
            difficulty=difficulty,
            focus_notes=focus,
            device_index=ACTIVE_DEVICE_INDEX,
            with_countdown=with_countdown,
            max_duration=max_duration,
        )

        if record_res is None:
            # User cancelled or failed
            if sys.stdin.isatty():
                retry = questionary.confirm("Recording was cancelled. Try again?", default=True).ask()
                if retry:
                    continue
            return

        audio_data, samplerate = record_res

        # Review loop
        action = "save" if auto_save or not sys.stdin.isatty() else None
        while action != "save":
            duration_sec = len(audio_data) / samplerate
            if sys.stdout.isatty():
                console.clear()
                console.print(make_header())
            console.print(preview_panel)
            console.print(
                Panel(
                    f"✔ [bold green]Voice Captured Successfully![/bold green]\n"
                    f"Duration: [bold yellow]{duration_sec:.1f} seconds[/bold yellow]  •  "
                    f"Sample Rate: [cyan]{samplerate} Hz[/cyan]",
                    border_style="green",
                    padding=(0, 2),
                )
            )

            action = questionary.select(
                "Review Your Recording:",
                choices=[
                    Choice("💾 Save & Generate NotebookLM Package", value="save"),
                    Choice("🔊 Play Back Recording", value="play"),
                    Choice("🔄 Re-record (Discard & Retry)", value="rerecord"),
                    Choice("❌ Discard & Return to Menu", value="discard"),
                ],
            ).ask()

            if action == "play":
                play_audio_array(audio_data, samplerate, title=f"Review: {title}")
                questionary.press_any_key_to_continue("Press any key to continue...").ask()
            elif action == "rerecord":
                break  # break out to recording loop
            elif action == "discard" or not action:
                console.print("[yellow]Recording discarded.[/yellow]")
                return

        if action == "save":
            # Export session
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_result = export_session(
                audio_data=audio_data,
                samplerate=samplerate,
                session_id=session_id,
                title=title,
                text=text,
                category=category,
                difficulty=difficulty,
                phonetic_focus=focus,
                auto_copy_prompt=True,
                boost_mode=active_boost,
            )

            # Show post-export success and actions
            if sys.stdin.isatty() and not auto_save:
                handle_post_export(export_result)
            else:
                console.print(f"[bold green]✔ Session exported to {export_result['session_dir']}[/bold green]")
                console.print(f"• Audio: {export_result['primary_audio_path']}")
                console.print(f"• Source Doc: {export_result['source_md_path']}")
                console.print(f"• Prompt File: {export_result['prompt_txt_path']}")
            break


def handle_post_export(res: Dict[str, Any]):
    """Display the export completion card and interactive NotebookLM quick actions."""
    console.clear()
    console.print(make_header())

    clipboard_status = (
        "[bold green]✔ Prompt copied to your clipboard automatically![/bold green]"
        if res.get("prompt_copied")
        else "[yellow]Note: Could not auto-copy to clipboard. You can copy it manually.[/yellow]"
    )

    audio_badge = "[bold green]AAC M4A (Lightweight & Crystal Clear)[/bold green]" if res.get("has_m4a") else "[yellow]Lossless WAV[/yellow]"
    gain_val = res.get("applied_gain_db", 0.0)
    boost_badge = f"[bold green]+{gain_val} dB (Auto-Speech Leveler)[/bold green]" if gain_val > 0 else "[dim]Standard Headroom[/dim]"

    summary_text = f"""
[bold green]🎉 Practice Session Exported Successfully![/bold green]

[bold cyan]Voice Loudness & Quality:[/bold cyan]
• [bold white]Audio Gain Applied:[/bold white] {boost_badge}
• [bold white]Audio Source:[/bold white]       `{res['primary_audio_path']}` ({audio_badge})
• [bold white]Text Context Source:[/bold white]  `{res['source_md_path']}`
• [bold white]NotebookLM Prompt:[/bold white]    `{res['prompt_txt_path']}`

{clipboard_status}

[bold yellow]How to analyze in NotebookLM in 30 seconds:[/bold yellow]
1. Open [cyan]https://notebooklm.google.com[/cyan].
2. Click **Add Sources** -> Drag & drop the audio file and `.md` file.
3. In the NotebookLM Chat box, press **Cmd + V** (Paste) and hit **Enter**!
"""

    console.print(Panel(summary_text.strip(), title="[bold cyan]NotebookLM Export Pack[/bold cyan]", border_style="cyan", padding=(1, 2)))

    # Quick interactive actions
    while True:
        next_act = questionary.select(
            "Quick Actions:",
            choices=[
                Choice("🌐 Open NotebookLM in Default Browser", value="open_nlm"),
                Choice("📂 Reveal Files in Finder (Drag-and-Drop)", value="finder"),
                Choice("🔊 Listen to Audio File", value="listen"),
                Choice("📋 Re-copy Prompt to Clipboard", value="recopy"),
                Choice("🏠 Return to Main Menu", value="menu"),
            ],
        ).ask()

        if next_act == "open_nlm":
            open_browser("https://notebooklm.google.com")
            console.print("[green]Opened https://notebooklm.google.com in browser.[/green]")
        elif next_act == "finder":
            reveal_in_finder(res["primary_audio_path"])
            console.print(f"[green]Revealed session in Finder.[/green]")
        elif next_act == "listen":
            play_audio_file(res["primary_audio_path"], title="Exported Audio")
        elif next_act == "recopy":
            with open(res["prompt_txt_path"], "r", encoding="utf-8") as f:
                p_text = f.read()
            copy_to_clipboard(p_text)
            console.print("[bold green]✔ Prompt re-copied to clipboard![/bold green]")
        elif next_act == "menu" or not next_act:
            break


def handle_browse_sessions():
    """Browse, inspect, and replay past practice sessions."""
    sessions = get_all_sessions()
    if not sessions:
        console.print("[yellow]No recordings found yet.[/yellow]")
        questionary.press_any_key_to_continue().ask()
        return

    console.clear()
    console.print(make_header())
    display_sessions_table(sessions)

    choices = [
        Choice(f"{s.get('created_at', '')} - {s.get('title', 'Session')[:35]} ({s.get('duration_str', '')})", value=s)
        for s in sessions
    ]
    choices.append(Choice("🔙 Back to Main Menu", value="back"))

    selected = questionary.select("Select a session to manage:", choices=choices).ask()
    if not selected or selected == "back":
        return

    # Session detail actions
    while True:
        act = questionary.select(
            f"Manage Session: {selected.get('title')}",
            choices=[
                Choice("🔊 Play Audio", value="play"),
                Choice("📂 Reveal in Finder", value="finder"),
                Choice("📋 Copy NotebookLM Prompt to Clipboard", value="prompt"),
                Choice("🌐 Open NotebookLM in Browser", value="nlm"),
                Choice("📖 View Reference Script", value="view"),
                Choice("🗑️  Delete Session", value="delete"),
                Choice("🔙 Back", value="back"),
            ],
        ).ask()

        if act == "play":
            audio_path = selected.get("primary_audio_path") or selected.get("wav_path")
            if audio_path and os.path.exists(audio_path):
                play_audio_file(audio_path, title=selected.get("title", "Session"))
            else:
                console.print("[red]Audio file missing.[/red]")
        elif act == "finder":
            audio_path = selected.get("primary_audio_path") or selected.get("wav_path")
            if audio_path:
                reveal_in_finder(audio_path)
        elif act == "prompt":
            p_path = selected.get("prompt_txt_path")
            if p_path and os.path.exists(p_path):
                with open(p_path, "r", encoding="utf-8") as f:
                    copy_to_clipboard(f.read())
                console.print("[bold green]✔ NotebookLM prompt copied to clipboard![/bold green]")
            else:
                console.print("[red]Prompt file not found.[/red]")
        elif act == "nlm":
            open_browser("https://notebooklm.google.com")
        elif act == "view":
            console.print(
                render_script_panel(
                    title=selected.get("title", ""),
                    text=selected.get("text", ""),
                    category=selected.get("category", ""),
                    difficulty=selected.get("difficulty", ""),
                    focus_notes=selected.get("phonetic_focus", ""),
                )
            )
            questionary.press_any_key_to_continue().ask()
        elif act == "delete":
            confirm = questionary.confirm("Are you sure you want to permanently delete this session?").ask()
            if confirm:
                delete_session(selected["folder_path"])
                console.print("[green]Session deleted successfully.[/green]")
                break
        elif act == "back" or not act:
            break


def handle_device_settings():
    """Device settings, microphone calibration, and volume boost."""
    global ACTIVE_DEVICE_INDEX, WITH_COUNTDOWN, VOICE_BOOST_MODE

    while True:
        console.clear()
        console.print(make_header())
        display_microphones_table()
        mics = list_microphones()

        current_name = "System Default"
        if ACTIVE_DEVICE_INDEX is not None:
            for m in mics:
                if m["index"] == ACTIVE_DEVICE_INDEX:
                    current_name = m["name"]
                    break

        countdown_str = "Enabled (3s)" if WITH_COUNTDOWN else "Disabled"
        sys_vol = get_macos_input_volume()
        sys_vol_str = f"{sys_vol}%" if sys_vol is not None else "N/A"

        boost_label = {
            "auto": "Auto Speech Leveler (Smart Boost)",
            "+6": "Gentle Boost (+6 dB / 2x)",
            "+12": "Medium Boost (+12 dB / 4x)",
            "+18": "High Boost (+18 dB / 8x)",
            "none": "Off (Standard Headroom)",
        }.get(VOICE_BOOST_MODE, VOICE_BOOST_MODE)

        choice = questionary.select(
            f"Audio Settings (Active Mic: {current_name}):",
            choices=[
                Choice("🎙️  Live Microphone VU Meter (Level Test)", value="test"),
                Choice("🔊 Quick 3-Sec Voice Test & Playback (Hear Your Volume)", value="quick_check"),
                Choice(f"⚡ Voice Booster Mode: [{boost_label}]", value="boost_mode"),
                Choice(f"🎚️  Set macOS Input Volume to 100% (Current: {sys_vol_str})", value="max_vol"),
                Choice("🔄 Change Active Input Microphone", value="change_mic"),
                Choice(f"⏱️  Toggle Countdown ({countdown_str})", value="toggle_countdown"),
                Choice("🔙 Back to Main Menu", value="back"),
            ],
        ).ask()

        if choice == "test":
            test_microphone_level(device_index=ACTIVE_DEVICE_INDEX)
            questionary.press_any_key_to_continue().ask()
        elif choice == "quick_check":
            run_quick_voice_check(device_index=ACTIVE_DEVICE_INDEX)
            questionary.press_any_key_to_continue().ask()
        elif choice == "boost_mode":
            b_choice = questionary.select(
                "Select Voice Booster Mode:",
                choices=[
                    Choice("⚡ Auto Speech Leveler (Recommended: boosts quiet voice up to +28 dB)", value="auto"),
                    Choice("🔊 Medium Boost (+12 dB / 4x volume)", value="+12"),
                    Choice("📢 High Boost (+18 dB / 8x volume)", value="+18"),
                    Choice("🔉 Gentle Boost (+6 dB / 2x volume)", value="+6"),
                    Choice("⏹️  Off (Raw input without leveling)", value="none"),
                ],
            ).ask()
            if b_choice:
                VOICE_BOOST_MODE = b_choice
                console.print(f"[bold green]✔ Voice booster mode set to: {VOICE_BOOST_MODE}[/bold green]")
                time.sleep(1)
        elif choice == "max_vol":
            ok = set_macos_input_volume(100)
            if ok:
                console.print("[bold green]✔ macOS microphone hardware volume set to 100%![/bold green]")
            else:
                console.print("[yellow]Could not set macOS input volume via AppleScript.[/yellow]")
            time.sleep(1.2)
        elif choice == "change_mic":
            mic_choices = [Choice(f"[{m['index']}] {m['name']}", value=m["index"]) for m in mics]
            mic_choices.append(Choice("Default System Mic", value=None))
            selected_idx = questionary.select("Select Microphone:", choices=mic_choices).ask()
            ACTIVE_DEVICE_INDEX = selected_idx
            console.print("[green]Active microphone updated.[/green]")
            time.sleep(0.8)
        elif choice == "toggle_countdown":
            WITH_COUNTDOWN = not WITH_COUNTDOWN
            console.print(f"[green]Countdown set to: {WITH_COUNTDOWN}[/green]")
            time.sleep(0.8)
        elif choice == "back" or not choice:
            break


def run_interactive_menu():
    """Launch the main interactive TUI menu."""
    while True:
        console.clear()
        console.print(make_header())

        menu_choice = questionary.select(
            "Main Menu:",
            choices=[
                Choice("🎯 Phrase Pronunciation Lab (Instant IPA, Tips & Real-Time Feedback)", value="phrase_coach"),
                Choice("🎙️  Long Practice Recording (Passages & Drills)", value="record"),
                Choice("📁 Browse Recording History", value="history"),
                Choice("🛠️  Audio & Microphone Settings", value="settings"),
                Choice("🧠 How to Use with NotebookLM", value="guide"),
                Choice("🚪 Exit", value="exit"),
            ],
        ).ask()

        if not menu_choice or menu_choice == "exit":
            console.print("\n[bold cyan]Thank you for using SpeakFlow! Happy speaking! 🎙️[/bold cyan]\n")
            break

        if menu_choice == "phrase_coach":
            handle_phrase_coach_flow()
        elif menu_choice == "record":
            item = select_practice_text()
            if item:
                handle_record_flow(item)
        elif menu_choice == "history":
            handle_browse_sessions()
        elif menu_choice == "settings":
            handle_device_settings()
        elif menu_choice == "guide":
            show_notebooklm_guide()


def main():
    """CLI entrypoint with argument parsing."""
    parser = argparse.ArgumentParser(
        prog="speakflow",
        description="SpeakFlow: Terminal Voice Studio for English Pronunciation Analysis in NotebookLM.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: phrase / coach
    phrase_parser = subparsers.add_parser("phrase", help="Instant IPA, pronunciation tips & real-time feedback for a phrase")
    phrase_parser.add_argument("phrase_text", nargs="?", default="Study of scarcity and choices", help="Phrase to practice")

    # Command: record
    rec_parser = subparsers.add_parser("record", help="Start a recording session directly")
    rec_parser.add_argument("--text", "-t", type=str, help="Reference text to read")
    rec_parser.add_argument("--file", "-f", type=str, help="Path to text or markdown file")
    rec_parser.add_argument("--title", type=str, default="CLI Recording", help="Title for the session")
    rec_parser.add_argument("--duration", "-d", type=float, default=None, help="Record for a fixed duration (seconds)")
    rec_parser.add_argument("--no-countdown", action="store_true", help="Skip the 3-second countdown")
    rec_parser.add_argument("--auto-save", action="store_true", help="Automatically save without review prompt")
    rec_parser.add_argument("--boost", "-b", type=str, default=None, help="Voice boost mode: auto, +6, +12, +18, none")

    # Command: list
    subparsers.add_parser("list", help="List all saved recording sessions")

    # Command: play
    play_parser = subparsers.add_parser("play", help="Play audio from a recording session")
    play_parser.add_argument("session", nargs="?", default="1", help="Session index (1, 2...) or session ID (e.g. session_20261031_201727)")

    # Command: test-mic
    subparsers.add_parser("test-mic", help="Test microphone audio level with live VU meter")

    # Command: guide
    subparsers.add_parser("guide", help="Show NotebookLM pronunciation guide")

    # Command: open-nlm
    subparsers.add_parser("open-nlm", help="Open Google NotebookLM in default browser")

    args = parser.parse_args()

    if args.command == "phrase":
        handle_phrase_coach_flow(args.phrase_text)
    elif args.command == "list":
        display_sessions_table()
    elif args.command == "play":
        sessions = get_all_sessions()
        if not sessions:
            console.print("[yellow]No recordings found.[/yellow]")
            return
        target_session = None
        # Try matching by index
        if args.session.isdigit():
            idx = int(args.session) - 1
            if 0 <= idx < len(sessions):
                target_session = sessions[idx]
        if not target_session:
            # Try matching by session_id or folder
            for s in sessions:
                if s.get("session_id") == args.session or Path(s.get("folder_path", "")).name == args.session:
                    target_session = s
                    break
        if not target_session:
            console.print(f"[red]Could not find session matching '{args.session}'. Run 'speakflow list' to see available sessions.[/red]")
            return

        audio_path = target_session.get("primary_audio_path") or target_session.get("wav_path")
        if audio_path and os.path.exists(audio_path):
            play_audio_file(audio_path, title=target_session.get("title", "Session"))
        else:
            console.print("[red]Audio file missing for this session.[/red]")
    elif args.command == "test-mic":
        test_microphone_level()
    elif args.command == "guide":
        show_notebooklm_guide()
    elif args.command == "open-nlm":
        open_browser("https://notebooklm.google.com")
    elif args.command == "record":
        text_content = ""
        title = args.title
        if args.file and os.path.exists(args.file):
            with open(args.file, "r", encoding="utf-8") as f:
                text_content = f.read().strip()
            if args.title == "CLI Recording":
                title = Path(args.file).stem.replace("_", " ").title()
        elif args.text:
            text_content = args.text
        else:
            item = select_practice_text()
            if item:
                handle_record_flow(
                    item,
                    max_duration=args.duration,
                    no_countdown=args.no_countdown,
                    auto_save=args.auto_save,
                    boost_mode=args.boost,
                )
            return

        if text_content:
            handle_record_flow(
                {
                    "id": f"cli_{int(datetime.now().timestamp())}",
                    "title": title,
                    "text": text_content,
                    "category": "CLI Practice",
                    "difficulty": "Custom",
                    "focus": "",
                },
                max_duration=args.duration,
                no_countdown=args.no_countdown,
                auto_save=args.auto_save,
                boost_mode=args.boost,
            )
    else:
        # Default: Launch interactive menu
        run_interactive_menu()


if __name__ == "__main__":
    main()
