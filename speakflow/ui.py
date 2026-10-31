"""
Rich UI Components, Styling, and Visualizers for SpeakFlow.
"""

import math
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED, DOUBLE, HEAVY

console = Console()

APP_TITLE = "🎙️  SPEAKFLOW STUDIO"
APP_SUBTITLE = "Voice Recording & Pronunciation Coach for NotebookLM"


def make_header() -> Panel:
    """Create a stylized application header."""
    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    
    title_text = Text()
    title_text.append("🎙️  SPEAKFLOW  🎙️\n", style="bold cyan")
    title_text.append("Terminal Voice Studio  •  Powered by Google NotebookLM", style="italic bright_white")
    
    return Panel(
        grid,
        box=ROUNDED,
        style="bold cyan on black",
        title="[bold yellow]English Pronunciation Coach[/bold yellow]",
        subtitle="[dim]v1.0.0[/dim]",
        padding=(0, 2),
    )


def format_vu_meter(rms: float, width: int = 26) -> Text:
    """
    Format a dynamic visual VU audio meter from RMS volume.
    Maps -60 dB to 0 dB into a filled bar.
    """
    if rms <= 1e-6:
        db = -60.0
    else:
        db = 20 * math.log10(rms)
        db = max(-60.0, min(0.0, db))

    # Normalized between 0.0 and 1.0
    norm = (db + 60.0) / 60.0
    filled = int(round(norm * width))
    filled = max(0, min(width, filled))
    empty = width - filled

    meter = Text()
    meter.append("[", style="bright_black")

    # Segment colors
    green_cutoff = int(width * 0.65)   # Up to -21 dB
    yellow_cutoff = int(width * 0.88)  # -21 dB to -7 dB

    for i in range(filled):
        if i < green_cutoff:
            meter.append("█", style="bold green")
        elif i < yellow_cutoff:
            meter.append("█", style="bold yellow")
        else:
            meter.append("█", style="bold red")

    meter.append("░" * empty, style="bright_black")
    meter.append("] ", style="bright_black")

    # dB readout
    db_style = "green" if db < -14 else ("yellow" if db < -3 else "bold red")
    meter.append(f"{db:5.1f} dB", style=db_style)
    return meter


def render_script_panel(
    title: str,
    text: str,
    category: str = "General",
    difficulty: str = "Intermediate",
    focus_notes: str = "",
) -> Panel:
    """Render the reference script in a comfortable teleprompter-style box."""
    word_count = len(text.split())
    # Est. duration at 130 wpm
    est_sec = max(5, int((word_count / 130) * 60))
    est_str = f"{est_sec // 60}:{est_sec % 60:02d}"

    content = Text()
    content.append(f"📖  {title}\n", style="bold bright_cyan")
    content.append(f"Category: {category}  •  Difficulty: {difficulty}  •  Length: {word_count} words (~{est_str})\n\n", style="dim italic")

    # Display text prominently
    content.append(f'"{text}"\n\n', style="bold bright_white")

    if focus_notes:
        content.append("🎯 Focus & Phonetics:\n", style="bold yellow")
        content.append(f"{focus_notes}\n", style="dim yellow")

    return Panel(
        content,
        title="[bold green]REFERENCE SCRIPT[/bold green]",
        border_style="cyan",
        box=ROUNDED,
        padding=(1, 3),
    )


def render_recording_dashboard(
    elapsed_sec: float,
    rms: float,
    peak: float,
    script_panel: Panel,
    is_paused: bool = False,
) -> Panel:
    """Render the live recording status dashboard."""
    m = int(elapsed_sec) // 60
    s = int(elapsed_sec) % 60
    timer_str = f"{m:02d}:{s:02d}"

    status_text = Text()
    if is_paused:
        status_text.append("⏸  PAUSED", style="bold yellow")
    else:
        status_text.append("●  RECORDING LIVE", style="bold blink red")

    status_text.append(f"   ⏱  {timer_str}   ", style="bold bright_white")
    status_text.append("  Level: ")
    status_text.append_text(format_vu_meter(rms, width=22))

    controls = Text("\n[Space] or [Enter] Finish & Save   •   [Ctrl+C] Cancel", style="bold yellow")

    dashboard_table = Table.grid(expand=True)
    dashboard_table.add_column()
    dashboard_table.add_row(script_panel)
    dashboard_table.add_row(
        Panel(
            Text.assemble(status_text, controls),
            box=HEAVY,
            border_style="red" if not is_paused else "yellow",
            style="on black",
            padding=(0, 2),
        )
    )

    return Panel(
        dashboard_table,
        box=ROUNDED,
        title="[bold red]STUDIO BOOTH[/bold red]",
        border_style="bright_black",
        padding=(0, 1),
    )
