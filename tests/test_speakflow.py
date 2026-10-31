"""
Unit tests for SpeakFlow components.
"""

import os
import shutil
import tempfile
import numpy as np
import pytest

from speakflow.prompts import generate_notebooklm_prompt, generate_source_document_markdown
from speakflow.library import PRACTICE_LIBRARY, get_categories, get_items_by_category, get_item_by_id
from speakflow.ui import format_vu_meter, render_script_panel
from speakflow.exporter import export_session, trim_silence, normalize_audio, smart_speech_boost, apply_manual_gain
from speakflow.sessions import get_all_sessions, delete_session
from speakflow.diagnostics import list_microphones


def test_practice_library():
    categories = get_categories()
    assert len(categories) >= 4
    assert "Tricky Phonemes" in categories
    assert "Tongue Twisters" in categories

    items = get_items_by_category("Tricky Phonemes")
    assert len(items) >= 2
    item = get_item_by_id("th_sounds")
    assert "thought" in item["text"].lower()


def test_prompts_generation():
    prompt = generate_notebooklm_prompt(
        title="Test Drill",
        text="The quick brown fox jumps over the lazy dog.",
        focus_notes="Focus on /ð/ sound."
    )
    assert "English Pronunciation and Speech Coach" in prompt
    assert "Word Accuracy & Fidelity Audit" in prompt
    assert "Phonetic & Pronunciation Analysis" in prompt
    assert "Target IPA vs Perceived IPA" in prompt
    assert "Tailored Action Drills" in prompt

    source_doc = generate_source_document_markdown(
        title="Test Drill",
        text="The quick brown fox jumps over the lazy dog.",
        session_id="session_test",
        timestamp="2026-10-31 20:00:00",
        duration_str="00:05",
        phonetic_focus="Focus on /ð/.",
    )
    assert "# SpeakFlow Pronunciation Practice Source" in source_doc
    assert "The quick brown fox" in source_doc


def test_vu_meter_formatting():
    quiet = format_vu_meter(0.0)
    assert "-60.0 dB" in quiet.plain

    med = format_vu_meter(0.1) # approx -20 dB
    assert "dB" in med.plain

    loud = format_vu_meter(1.0) # 0 dB
    assert "0.0 dB" in loud.plain


def test_smart_speech_boost():
    # Simulate very quiet voice (RMS ~ -40 dB)
    sr = 44100
    quiet_voice = np.random.normal(0, 0.01, sr).astype(np.float32)
    boosted, gain_db = smart_speech_boost(quiet_voice, target_rms_db=-16.0)

    assert gain_db > 15.0  # Should apply substantial gain to small voice
    boosted_rms = np.sqrt(np.mean(boosted ** 2))
    boosted_rms_db = 20 * np.log10(boosted_rms)
    assert boosted_rms_db > -22.0  # Loud and clear speech level
    assert np.max(np.abs(boosted)) <= 1.0  # No clipping


def test_audio_processing_and_export():
    tmp_dir = tempfile.mkdtemp()
    try:
        sr = 44100
        # Generate 1 sec sine wave
        t = np.linspace(0, 1.0, sr, endpoint=False)
        tone = 0.3 * np.sin(2 * np.pi * 440 * t)

        # Pad with 0.5s silence before and after
        silence = np.zeros(int(0.5 * sr))
        padded = np.concatenate([silence, tone, silence])

        trimmed = trim_silence(padded, threshold_db=-40, sr=sr)
        assert len(trimmed) < len(padded)

        norm = normalize_audio(trimmed, target_peak_db=-1.5)
        peak = np.max(np.abs(norm))
        expected_amp = 10 ** (-1.5 / 20.0)
        assert np.isclose(peak, expected_amp, atol=1e-3)

        # Test session export
        res = export_session(
            audio_data=norm,
            samplerate=sr,
            session_id="test_sess_01",
            title="Test Session",
            text="Hello world test",
            base_dir=tmp_dir,
            auto_copy_prompt=False,
        )

        assert os.path.exists(res["primary_audio_path"])
        assert os.path.exists(res["source_md_path"])
        assert os.path.exists(res["prompt_txt_path"])
        assert res["has_m4a"] is True  # macOS afconvert produces m4a

        # Test session loading
        sessions = get_all_sessions(base_dir=tmp_dir)
        assert len(sessions) == 1
        assert sessions[0]["title"] == "Test Session"

        # Test session deletion
        deleted = delete_session(sessions[0]["folder_path"])
        assert deleted is True
        assert len(get_all_sessions(base_dir=tmp_dir)) == 0

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_list_microphones():
    mics = list_microphones()
    assert len(mics) > 0
    assert any("Microphone" in m["name"] for m in mics)
