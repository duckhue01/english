"""
Session History and Storage Manager for SpeakFlow.
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table

console = Console()
DEFAULT_RECORDINGS_DIR = "recordings"


def get_all_sessions(base_dir: str = DEFAULT_RECORDINGS_DIR) -> List[Dict[str, Any]]:
    """Scan the recordings directory and return all saved session metadata."""
    base_path = Path(base_dir)
    if not base_path.exists():
        return []

    sessions = []
    for entry in sorted(base_path.iterdir(), reverse=True):
        if entry.is_dir():
            meta_file = entry / "session_meta.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["folder_path"] = str(entry)
                        sessions.append(data)
                except Exception:
                    continue
    return sessions


def display_sessions_table(sessions: Optional[List[Dict[str, Any]]] = None, base_dir: str = DEFAULT_RECORDINGS_DIR):
    """Render a clean summary table of recorded sessions."""
    if sessions is None:
        sessions = get_all_sessions(base_dir)

    if not sessions:
        console.print("[yellow]No recordings found yet. Choose 'New Practice Recording' to start![/yellow]")
        return

    table = Table(title="📁 Practice Recording Library", header_style="bold cyan", border_style="dim")
    table.add_column("#", justify="center", style="dim")
    table.add_column("Session Date", style="bright_white")
    table.add_column("Title / Topic", style="bold cyan")
    table.add_column("Duration", justify="center", style="yellow")
    table.add_column("Audio Format", justify="center", style="green")
    table.add_column("Preview", style="italic bright_black")

    for i, s in enumerate(sessions, 1):
        # Format check
        fmt = "M4A + WAV" if s.get("m4a_path") and os.path.exists(s["m4a_path"]) else "WAV"
        preview = s.get("text", "")[:45] + "..." if len(s.get("text", "")) > 45 else s.get("text", "")

        table.add_row(
            str(i),
            s.get("created_at", "Unknown"),
            s.get("title", "Practice"),
            s.get("duration_str", "00:00"),
            fmt,
            preview,
        )

    console.print(table)


def delete_session(session_folder: str) -> bool:
    """Delete a recording session directory."""
    path = Path(session_folder)
    if path.exists() and path.is_dir():
        shutil.rmtree(path)
        return True
    return False
