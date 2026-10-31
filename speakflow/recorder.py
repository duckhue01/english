"""
Audio Recording Engine for SpeakFlow.
Handles non-blocking microphone recording, real-time VU meter updates,
teleprompter display, and countdown timers.
"""

import sys
import time
import select
import termios
import tty
from typing import Optional, Tuple
import numpy as np
import sounddevice as sd
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from speakflow.ui import render_script_panel, render_recording_dashboard

console = Console()


def run_countdown(seconds: int = 3, script_panel: Optional[Panel] = None):
    """Display an energetic countdown before recording starts."""
    for i in range(seconds, 0, -1):
        count_text = Text()
        count_text.append(f"\n   Get Ready to Speak: {i}   \n", style="bold yellow on bright_black")

        display_panel = Panel(
            count_text,
            title="[bold yellow]PREPARING MICROPHONE[/bold yellow]",
            border_style="yellow",
            padding=(0, 2),
        )
        if sys.stdout.isatty():
            console.clear()
        if script_panel:
            console.print(script_panel)
        console.print(display_panel)
        time.sleep(1.0)

    if sys.stdout.isatty():
        console.clear()


def record_session(
    title: str,
    text: str,
    category: str = "General",
    difficulty: str = "Intermediate",
    focus_notes: str = "",
    samplerate: int = 44100,
    device_index: Optional[int] = None,
    with_countdown: bool = True,
    max_duration: Optional[float] = None,
) -> Optional[Tuple[np.ndarray, int]]:
    """
    Record voice while displaying the teleprompter text and live audio level.
    Pressing [Space], [Enter], or [q] stops the recording cleanly.
    Pressing [Ctrl+C] aborts.
    """
    script_panel = render_script_panel(
        title=title,
        text=text,
        category=category,
        difficulty=difficulty,
        focus_notes=focus_notes,
    )

    if with_countdown:
        run_countdown(seconds=3, script_panel=script_panel)

    buffer = []
    current_rms = [0.0]
    current_peak = [0.0]

    def audio_callback(indata, frames, time_info, status):
        data_copy = indata.copy()
        buffer.append(data_copy)
        # Compute RMS and peak for VU meter
        mono = data_copy[:, 0] if data_copy.ndim > 1 else data_copy
        rms = float(np.sqrt(np.mean(mono ** 2)))
        peak = float(np.max(np.abs(mono)))
        current_rms[0] = rms
        current_peak[0] = peak

    stream_kwargs = {
        "samplerate": samplerate,
        "channels": 1,
        "dtype": "float32",
        "callback": audio_callback,
    }
    if device_index is not None:
        stream_kwargs["device"] = device_index

    # Check terminal TTY availability
    is_tty = sys.stdin.isatty()
    old_settings = None
    fd = None

    if is_tty:
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:
            is_tty = False

    start_time = time.time()
    aborted = False

    try:
        with sd.InputStream(**stream_kwargs):
            with Live(console=console, refresh_per_second=15, screen=False) as live:
                while True:
                    elapsed = time.time() - start_time
                    dashboard = render_recording_dashboard(
                        elapsed_sec=elapsed,
                        rms=current_rms[0],
                        peak=current_peak[0],
                        script_panel=script_panel,
                    )
                    live.update(dashboard)

                    if max_duration is not None and elapsed >= max_duration:
                        break

                    # Check for keypress if TTY is available
                    if is_tty:
                        r, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if r:
                            ch = sys.stdin.read(1)
                            # Space (' '), Enter ('\n' or '\r'), or 'q' stops
                            if ch in (" ", "\n", "\r", "q", "Q"):
                                break
                    else:
                        time.sleep(0.05)

    except KeyboardInterrupt:
        aborted = True
    finally:
        # Restore terminal settings
        if is_tty and old_settings is not None and fd is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass
        if sys.stdout.isatty():
            console.clear()

    if aborted:
        console.print("[yellow]Recording cancelled by user.[/yellow]")
        return None

    if not buffer:
        console.print("[red]No audio captured.[/red]")
        return None

    full_audio = np.concatenate(buffer, axis=0)
    total_sec = len(full_audio) / samplerate

    if total_sec < 0.5:
        console.print("[yellow]Recording too short (< 0.5s). Discarded.[/yellow]")
        return None

    return full_audio, samplerate
