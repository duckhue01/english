"""High-fidelity Text-To-Speech (TTS) engine with natural tempo control and caching."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

TTS_CACHE_DIR = Path("data/tts_cache")
DEFAULT_VOICE = "Samantha"

# Words per minute for distinct, natural tempos
SPEED_WPM = {
    "slow": 100,
    "normal": 175,
    "fast": 245,
}


def get_wpm(speed: str | float | int) -> int:
    if isinstance(speed, (int, float)):
        if speed <= 0.75:
            return SPEED_WPM["slow"]
        elif speed >= 1.2:
            return SPEED_WPM["fast"]
        else:
            return SPEED_WPM["normal"]

    s = str(speed).strip().lower()
    return SPEED_WPM.get(s, SPEED_WPM["normal"])


def synthesize_speech(text: str, speed: str | float | int = "normal", voice: str = DEFAULT_VOICE) -> Path:
    """Synthesizes text into high-quality AAC audio file, returning the path to the cached audio."""
    clean_text = text.strip()[:1000]
    if not clean_text:
        raise ValueError("Text cannot be empty")

    wpm = get_wpm(speed)
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_key = hashlib.sha256(f"{clean_text}_{voice}_{wpm}".encode("utf-8")).hexdigest()[:24]
    cached_file = TTS_CACHE_DIR / f"{cache_key}.m4a"

    if cached_file.exists() and cached_file.stat().st_size > 0:
        return cached_file

    say_bin = shutil.which("say")
    afconvert_bin = shutil.which("afconvert")

    if not say_bin or not afconvert_bin:
        raise RuntimeError("Native macOS TTS tools (say/afconvert) are not available")

    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as aiff_f:
        aiff_path = aiff_f.name

    try:
        # Run say with exact WPM rate
        subprocess.run(
            [say_bin, "-v", voice, "-r", str(wpm), clean_text, "-o", aiff_path],
            check=True,
            timeout=10,
        )
        # Convert to compressed, clean AAC m4a
        subprocess.run(
            [afconvert_bin, "-f", "m4af", "-d", "aac", aiff_path, str(cached_file)],
            check=True,
            timeout=10,
        )
    finally:
        if os.path.exists(aiff_path):
            try:
                os.remove(aiff_path)
            except OSError:
                pass

    return cached_file
