"""
Audio Playback Engine for SpeakFlow.
Allows users to listen to their voice recording immediately in the terminal.
"""

import sys
import time
import subprocess
from typing import Optional
import numpy as np
import sounddevice as sd
import soundfile as sf
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.text import Text

console = Console()


def speak_phrase(phrase: str, rate: int = 140) -> bool:
    """
    Play native reference pronunciation using macOS native speech synthesizer.
    """
    try:
        console.print(f"[bold cyan]🗣️  Native Pronunciation Model:[/bold cyan] [bright_white]\"{phrase}\"[/bright_white]")
        subprocess.run(["say", "-r", str(rate), phrase], check=True)
        return True
    except Exception as e:
        console.print(f"[yellow]Could not play speech model: {e}[/yellow]")
        return False


def play_audio_file(filepath: str, title: str = "Audio Playback") -> bool:
    """
    Play an audio file (WAV, M4A, etc.) using macOS native afplay or soundfile.
    Displays a playback status in the terminal.
    """
    # If it's a WAV file, we can read it and play via sounddevice with a live progress bar
    if filepath.endswith(".wav"):
        try:
            data, sr = sf.read(filepath)
            return play_audio_array(data, sr, title=title)
        except Exception:
            pass

    # Native afplay fallback (supports M4A, AAC, MP3, WAV directly)
    try:
        console.print(f"[bold cyan]▶ Playing:[/bold cyan] [bright_white]{title}[/bright_white] [dim]({filepath})[/dim]")
        proc = subprocess.Popen(["afplay", filepath])
        console.print("[dim italic]Press Ctrl+C to stop playback...[/dim italic]")
        proc.wait()
        return True
    except KeyboardInterrupt:
        if proc:
            proc.terminate()
        console.print("\n[yellow]Playback stopped.[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]Error playing audio: {e}[/red]")
        return False


def play_audio_array(data: np.ndarray, samplerate: int = 44100, title: str = "Playback") -> bool:
    """
    Play an in-memory numpy audio array with a visual progress bar.
    """
    total_samples = len(data)
    duration = total_samples / samplerate
    if duration <= 0:
        return False

    sd.stop()
    sd.play(data, samplerate)

    start_time = time.time()
    try:
        with Live(console=console, refresh_per_second=10) as live:
            while True:
                elapsed = time.time() - start_time
                if elapsed >= duration or not sd.get_stream().active:
                    break

                pct = min(1.0, elapsed / duration)
                bar_len = 30
                filled = int(round(pct * bar_len))
                bar_str = "━" * filled + "╸" + "─" * max(0, bar_len - filled - 1)

                cur_m, cur_s = int(elapsed) // 60, int(elapsed) % 60
                tot_m, tot_s = int(duration) // 60, int(duration) % 60

                msg = Text()
                msg.append("🔊 Playing: ", style="bold cyan")
                msg.append(f"{title}\n", style="bold bright_white")
                msg.append(f"[{bar_str[:bar_len]}] ", style="bold green")
                msg.append(f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}", style="dim")
                msg.append("  (Press Ctrl+C to stop)", style="italic bright_black")

                live.update(
                    Panel(
                        msg,
                        title="[cyan]AUDIO MONITOR[/cyan]",
                        border_style="cyan",
                        padding=(0, 2),
                    )
                )
                time.sleep(0.08)

        sd.wait()
        return True
    except KeyboardInterrupt:
        sd.stop()
        console.print("\n[yellow]Playback stopped.[/yellow]")
        return False
