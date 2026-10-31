"""
Audio Diagnostics, Device Selection, and Volume Calibration for SpeakFlow.
Allows users to list microphones, calibrate levels, adjust macOS input volume,
and run quick voice test playbacks.
"""

import sys
import time
import select
import termios
import tty
import subprocess
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import sounddevice as sd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from speakflow.ui import format_vu_meter
from speakflow.player import play_audio_array

console = Console()


def get_macos_input_volume() -> Optional[int]:
    """Get current macOS microphone input volume (0-100) via AppleScript."""
    try:
        cmd = ["osascript", "-e", "input volume of (get volume settings)"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(res.stdout.strip())
    except Exception:
        return None


def set_macos_input_volume(volume: int) -> bool:
    """Set macOS microphone input volume (0-100) via AppleScript."""
    try:
        volume = max(0, min(100, volume))
        cmd = ["osascript", "-e", f"set volume input volume {volume}"]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception:
        return False


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
    """Print a clean table of all input devices and system volume."""
    devices = list_microphones()
    sys_vol = get_macos_input_volume()
    vol_str = f"{sys_vol}%" if sys_vol is not None else "Unknown"

    table = Table(
        title=f"🎤 Microphones & Input Hardware (macOS Input Volume: {vol_str})",
        header_style="bold cyan",
        border_style="dim",
    )
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


def run_quick_voice_check(device_index: Optional[int] = None):
    """
    Record 3 seconds of voice, apply smart boost, and immediately play it back
    so the user can hear their true output volume in real-time.
    """
    from speakflow.exporter import smart_speech_boost

    sr = 44100
    duration = 3.0
    console.print("\n[bold cyan]🎙️ Quick 3-Second Voice Test[/bold cyan]")
    console.print("[yellow]Say something now (e.g. 'Testing one two three, hello world!')...[/yellow]")

    buffer = []

    def callback(indata, frames, time_info, status):
        buffer.append(indata.copy())

    stream_kwargs = {
        "samplerate": sr,
        "channels": 1,
        "dtype": "float32",
        "callback": callback,
    }
    if device_index is not None:
        stream_kwargs["device"] = device_index

    with sd.InputStream(**stream_kwargs):
        for i in range(int(duration * 10)):
            sys.stdout.write(f"\r● Recording... [{'=' * (i + 1)}{' ' * (30 - i - 1)}] {duration - (i/10):0.1f}s")
            sys.stdout.flush()
            time.sleep(0.1)

    print("\n")
    if not buffer:
        console.print("[red]No audio captured.[/red]")
        return

    raw = np.concatenate(buffer, axis=0)
    raw_peak = np.max(np.abs(raw))
    raw_rms = np.sqrt(np.mean(raw**2))
    raw_rms_db = 20 * np.log10(max(1e-6, raw_rms))

    boosted, gain_db = smart_speech_boost(raw, target_rms_db=-16.0)
    boosted_rms = np.sqrt(np.mean(boosted**2))
    boosted_rms_db = 20 * np.log10(max(1e-6, boosted_rms))

    console.print(f"[dim]Raw Voice Volume:    {raw_rms_db:5.1f} dB[/dim]")
    console.print(f"[bold green]✔ Auto-Boost Applied: +{gain_db:5.1f} dB (Output: {boosted_rms_db:5.1f} dB)[/bold green]")
    console.print("[cyan]🔊 Playing back your boosted voice now...[/cyan]")
    play_audio_array(boosted, sr, title="3-Second Voice Test Playback")


def test_microphone_level(device_index: Optional[int] = None, duration_sec: int = 12):
    """
    Interactive microphone level tester with real-time VU meter.
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

    # Check system volume
    sys_vol = get_macos_input_volume()
    if sys_vol is not None and sys_vol < 80:
        console.print(f"[yellow]⚠️  Notice: macOS microphone hardware volume is currently set to {sys_vol}%.[/yellow]")
        console.print("[dim]Tip: You can maximize system input volume in Settings.[/dim]\n")

    console.print("[bold cyan]🎙️ Live Microphone VU Meter[/bold cyan]")
    console.print("[dim]Speak normally into your microphone. Watch the level meter below:[/dim]")
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

    peak_db = 20 * np.log10(max(1e-6, peak_rms[0]))
    console.print("[bold green]✔ Test finished.[/bold green]")
    if peak_db < -35.0:
        console.print(f"[bold yellow]⚠️  Your raw microphone input is very quiet (Peak: {peak_db:.1f} dB).[/bold yellow]")
        console.print("[yellow]SpeakFlow's Smart Speech Booster will automatically boost your voice by up to +26 dB on export.[/yellow]")
    else:
        console.print(f"[bold green]✔ Signal detected (Peak: {peak_db:.1f} dB). Ready to record![/bold green]")
