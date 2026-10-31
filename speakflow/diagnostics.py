"""
Audio Diagnostics and Device Selection for SpeakFlow.
Allows users to list microphones, test input volume, and calibrate levels.
"""

import sys
import time
import select
import termios
import tty
from typing import List, Dict, Any, Optional
import numpy as np
import sounddevice as sd
from rich.console import Console
from rich.table import Table
from rich.text import Text

from speakflow.ui import format_vu_meter

console = Console()


def list_microphones() -> List[Dict[str, Any]]:
    """Get all available input audio devices on macOS."""
    devices = sd.query_devices()
    default_in = sd.default.device[0]

    inputs = []
    for idx, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            inputs.append({
                "index": idx,
                "name": d.get("name", f"Device #{idx}"),
                "channels": d.get("max_input_channels", 1),
                "samplerate": int(d.get("default_samplerate", 44100)),
                "is_default": (idx == default_in),
            })
    return inputs


def display_microphones_table():
    """Print a clean table of all input devices."""
    devices = list_microphones()
    table = Table(title="🎤 Available Microphones", header_style="bold cyan", border_style="dim")
    table.add_column("ID", justify="center", style="bold yellow")
    table.add_column("Device Name", style="bright_white")
    table.add_column("Channels", justify="center", style="dim")
    table.add_column("Default Rate", justify="right", style="dim")
    table.add_column("Status", justify="center")

    for d in devices:
        status = "[bold green]Active Default[/bold green]" if d["is_default"] else "[dim]Available[/dim]"
        table.add_row(
            str(d["index"]),
            d["name"],
            str(d["channels"]),
            f"{d['samplerate']} Hz",
            status,
        )

    console.print(table)


def test_microphone_level(device_index: Optional[int] = None, duration_sec: int = 10):
    """
    Run an interactive microphone test with real-time VU meter.
    Allows testing voice sensitivity and background noise.
    """
    current_rms = [0.0]
    peak_rms = [0.0]

    def callback(indata, frames, time_info, status):
        mono = indata[:, 0] if indata.ndim > 1 else indata
        rms = float(np.sqrt(np.mean(mono ** 2)))
        current_rms[0] = rms
        if rms > peak_rms[0]:
            peak_rms[0] = rms

    stream_kwargs = {
        "samplerate": 44100,
        "channels": 1,
        "dtype": "float32",
        "callback": callback,
    }
    if device_index is not None:
        stream_kwargs["device"] = device_index

    is_tty = sys.stdin.isatty()
    old_settings = None
    fd = None

    console.print("\n[bold cyan]🎙️ Testing Microphone Audio Levels[/bold cyan]")
    console.print("[dim]Speak naturally to test volume and background noise.[/dim]")
    if is_tty:
        console.print("[yellow]Press [Space] or [Enter] when done to exit tester.\n[/yellow]")

    start_time = time.time()
    try:
        if is_tty:
            try:
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                tty.setcbreak(fd)
            except Exception:
                is_tty = False

        with sd.InputStream(**stream_kwargs):
            while time.time() - start_time < duration_sec:
                rms = current_rms[0]
                vu = format_vu_meter(rms, width=32)

                text = Text()
                text.append("Live Mic Level: ")
                text.append_text(vu)
                text.append(f"  (Peak: {20 * np.log10(max(1e-6, peak_rms[0])):5.1f} dB)", style="dim")

                if sys.stdout.isatty():
                    sys.stdout.write("\r" + text.markup)
                    sys.stdout.flush()

                if is_tty:
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        sys.stdin.read(1)
                        break
                else:
                    time.sleep(0.08)
    except KeyboardInterrupt:
        pass
    finally:
        if is_tty and old_settings is not None and fd is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass
        print("\n")

    console.print("[bold green]✔ Microphone test complete.[/bold green]")
    if peak_rms[0] < 0.005:
        console.print("[bold yellow]⚠️  Warning: Audio level was very quiet. Speak closer to the mic or adjust input volume in macOS System Settings.[/bold yellow]")
    else:
        console.print(f"[bold green]✔ Signal detected (Peak: {20 * np.log10(max(1e-6, peak_rms[0])):0.1f} dB). Ready to record![/bold green]")
