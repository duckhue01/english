"""
Export Engine for SpeakFlow.
Handles audio normalization, WAV export, M4A conversion (via native afconvert),
and generation of NotebookLM-ready source documents and prompts.
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np
import soundfile as sf
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from speakflow.prompts import generate_notebooklm_prompt, generate_source_document_markdown

console = Console()


def trim_silence(data: np.ndarray, threshold_db: float = -45.0, pad_sec: float = 0.2, sr: int = 44100) -> np.ndarray:
    """
    Trim silence at the start and end of recording, leaving a small comfortable padding.
    """
    if len(data) == 0:
        return data

    # Flatten if multi-channel
    samples = data.flatten()
    abs_samples = np.abs(samples)

    # Convert threshold to linear amplitude
    thresh_amp = 10 ** (threshold_db / 20.0)
    non_silent_indices = np.where(abs_samples > thresh_amp)[0]

    if len(non_silent_indices) == 0:
        return data  # all silent or very quiet, keep original

    pad_samples = int(pad_sec * sr)
    start_idx = max(0, non_silent_indices[0] - pad_samples)
    end_idx = min(len(samples), non_silent_indices[-1] + pad_samples)

    return samples[start_idx:end_idx]


def smart_speech_boost(
    audio: np.ndarray,
    target_rms_db: float = -16.0,
    max_gain_db: float = 28.0,
    peak_limit_db: float = -1.0,
) -> Tuple[np.ndarray, float]:
    """
    Intelligent Speech Leveler & Soft Limiter for voice recordings:
    1. Removes DC bias / microphone rumble.
    2. Identifies active spoken speech energy (ignoring silent pauses).
    3. Calculates makeup gain to bring quiet speech to standard broadcast/podcast volume.
    4. Applies transparent soft-knee saturation (tanh) to tame plosives or loud spikes.
    """
    if len(audio) == 0:
        return audio, 0.0

    # 1. Remove DC bias
    audio = (audio - np.mean(audio)).astype(np.float32)

    # 2. Analyze active speech frames (50ms frames)
    frame_len = 2048
    hop_len = 1024
    if len(audio) < frame_len:
        speech_rms = float(np.sqrt(np.mean(audio ** 2)))
    else:
        n_frames = max(1, (len(audio) - frame_len) // hop_len)
        energies = []
        for i in range(n_frames):
            chunk = audio[i * hop_len : i * hop_len + frame_len]
            rms = np.sqrt(np.mean(chunk ** 2))
            if rms > 1e-4:  # Above -80 dB
                energies.append(rms)

        if energies:
            # 75th percentile represents typical spoken volume
            speech_rms = float(np.percentile(energies, 75))
        else:
            speech_rms = float(np.sqrt(np.mean(audio ** 2)))

    if speech_rms <= 1e-6:
        return audio, 0.0

    # 3. Calculate necessary gain
    current_rms_db = 20.0 * np.log10(speech_rms)
    needed_gain_db = target_rms_db - current_rms_db
    applied_gain_db = max(0.0, min(max_gain_db, needed_gain_db))
    linear_gain = 10.0 ** (applied_gain_db / 20.0)

    boosted = audio * linear_gain

    # 4. Soft-knee limiter at peak_limit_db to prevent clipping
    peak_threshold = 10.0 ** (peak_limit_db / 20.0)
    current_peak = np.max(np.abs(boosted))

    if current_peak > peak_threshold:
        # Smoothly saturate using soft tanh curve
        ratio = boosted / peak_threshold
        compressed = np.tanh(ratio) * peak_threshold
        return compressed.astype(np.float32), applied_gain_db
    else:
        return boosted.astype(np.float32), applied_gain_db


def apply_manual_gain(
    audio: np.ndarray,
    gain_db: float,
    peak_limit_db: float = -1.0,
) -> Tuple[np.ndarray, float]:
    """Apply fixed gain boost in dB with soft limiter."""
    if len(audio) == 0:
        return audio, 0.0

    audio = (audio - np.mean(audio)).astype(np.float32)
    linear_gain = 10.0 ** (gain_db / 20.0)
    boosted = audio * linear_gain

    peak_threshold = 10.0 ** (peak_limit_db / 20.0)
    current_peak = np.max(np.abs(boosted))

    if current_peak > peak_threshold:
        ratio = boosted / peak_threshold
        compressed = np.tanh(ratio) * peak_threshold
        return compressed.astype(np.float32), gain_db
    else:
        return boosted.astype(np.float32), gain_db


def normalize_audio(data: np.ndarray, target_peak_db: float = -1.5) -> np.ndarray:
    """
    Standard peak normalization (fallback).
    """
    if len(data) == 0:
        return data

    peak = np.max(np.abs(data))
    if peak <= 1e-6:
        return data

    target_amp = 10 ** (target_peak_db / 20.0)
    gain = target_amp / peak
    return (data * gain).astype(np.float32)


def convert_wav_to_m4a(wav_path: str, m4a_path: str) -> bool:
    """
    Convert WAV to high quality AAC M4A using macOS native afconvert.
    AAC is lightweight, pristine quality, and natively supported by Google NotebookLM.
    """
    try:
        cmd = ["afconvert", "-f", "m4af", "-d", "aac", "-b", "192000", wav_path, m4a_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and os.path.exists(m4a_path)
    except Exception as e:
        console.print(f"[dim yellow]Notice: afconvert conversion failed ({e}), keeping WAV.[/dim yellow]")
        return False


def copy_to_clipboard(text: str) -> bool:
    """Copy text to macOS system clipboard using pbcopy."""
    try:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"))
        return proc.returncode == 0
    except Exception:
        return False


def open_browser(url: str = "https://notebooklm.google.com") -> bool:
    """Open URL in the user's default browser."""
    try:
        subprocess.run(["open", url], check=True)
        return True
    except Exception:
        return False


def reveal_in_finder(path: str) -> bool:
    """Reveal file or folder in macOS Finder."""
    try:
        subprocess.run(["open", "-R", path], check=True)
        return True
    except Exception:
        return False


def export_session(
    audio_data: np.ndarray,
    samplerate: int,
    session_id: str,
    title: str,
    text: str,
    category: str = "General",
    difficulty: str = "Intermediate",
    phonetic_focus: str = "",
    base_dir: str = "recordings",
    auto_copy_prompt: bool = True,
    boost_mode: str = "auto",
) -> Dict[str, Any]:
    """
    Export the complete session:
    1. Trim Silence.
    2. Apply Smart Speech Boost / Leveler (up to +28dB clean gain).
    3. Write audio.wav.
    4. Convert to audio.m4a (preferred for NotebookLM).
    5. Write notebooklm_source.md.
    6. Write notebooklm_prompt.txt.
    7. Automatically copy prompt to macOS clipboard.
    """
    # Create session directory
    session_dir = Path(base_dir) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Process audio
    trimmed = trim_silence(audio_data, sr=samplerate)

    # Apply voice gain boost
    applied_gain_db = 0.0
    if boost_mode == "auto":
        processed_audio, applied_gain_db = smart_speech_boost(trimmed, target_rms_db=-16.0)
    elif boost_mode.startswith("+") or boost_mode.replace(".", "", 1).isdigit():
        try:
            val = float(boost_mode.replace("+", "").replace("db", "").strip())
            processed_audio, applied_gain_db = apply_manual_gain(trimmed, gain_db=val)
        except ValueError:
            processed_audio, applied_gain_db = smart_speech_boost(trimmed, target_rms_db=-16.0)
    else:
        processed_audio = normalize_audio(trimmed)

    duration_sec = len(processed_audio) / samplerate
    m = int(duration_sec) // 60
    s = int(duration_sec) % 60
    duration_str = f"{m:02d}:{s:02d}"

    # Export paths
    wav_path = str(session_dir / f"{session_id}_audio.wav")
    m4a_path = str(session_dir / f"{session_id}_audio.m4a")
    source_md_path = str(session_dir / f"{session_id}_notebooklm_source.md")
    prompt_txt_path = str(session_dir / f"{session_id}_notebooklm_prompt.txt")
    meta_json_path = str(session_dir / "session_meta.json")

    # 1. Save WAV
    sf.write(wav_path, processed_audio, samplerate, subtype="PCM_16")

    # 2. Convert to M4A
    has_m4a = convert_wav_to_m4a(wav_path, m4a_path)
    primary_audio_path = m4a_path if has_m4a else wav_path

    # Timestamp
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # 3. Generate Source Markdown
    source_content = generate_source_document_markdown(
        title=title,
        text=text,
        session_id=session_id,
        timestamp=timestamp_str,
        duration_str=duration_str,
        category=category,
        phonetic_focus=phonetic_focus,
        difficulty=difficulty,
    )
    with open(source_md_path, "w", encoding="utf-8") as f:
        f.write(source_content)

    # 4. Generate Prompt Text
    prompt_content = generate_notebooklm_prompt(
        title=title,
        text=text,
        focus_notes=phonetic_focus,
    )
    with open(prompt_txt_path, "w", encoding="utf-8") as f:
        f.write(prompt_content)

    # Copy prompt to clipboard
    prompt_copied = False
    if auto_copy_prompt:
        prompt_copied = copy_to_clipboard(prompt_content)

    # Meta
    meta = {
        "session_id": session_id,
        "title": title,
        "text": text,
        "category": category,
        "difficulty": difficulty,
        "phonetic_focus": phonetic_focus,
        "duration_sec": duration_sec,
        "duration_str": duration_str,
        "applied_gain_db": round(applied_gain_db, 1),
        "boost_mode": boost_mode,
        "created_at": timestamp_str,
        "wav_path": wav_path,
        "m4a_path": m4a_path if has_m4a else None,
        "primary_audio_path": primary_audio_path,
        "source_md_path": source_md_path,
        "prompt_txt_path": prompt_txt_path,
    }

    import json
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return {
        "meta": meta,
        "session_dir": str(session_dir),
        "primary_audio_path": primary_audio_path,
        "source_md_path": source_md_path,
        "prompt_txt_path": prompt_txt_path,
        "prompt_copied": prompt_copied,
        "duration_str": duration_str,
        "applied_gain_db": round(applied_gain_db, 1),
        "has_m4a": has_m4a,
    }
