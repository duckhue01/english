from __future__ import annotations

import io
import numpy as np
import soundfile as sf

from app.pron.scoring import (
    score_with_wav2vec2_alignment,
    score_with_whisper,
    text_to_phonemes_ipa,
)


def test_text_to_phonemes_ipa():
    res = text_to_phonemes_ipa("think")
    assert len(res) == 1
    w = res[0]
    assert w["word"] == "think"
    assert w["arpabet"] == ["TH", "IH1", "NG", "K"]
    assert "θ" in w["ipa"]
    assert "ŋ" in w["ipa"]

    # Test sentence
    res2 = text_to_phonemes_ipa("specialization increases productivity")
    assert len(res2) == 3
    assert res2[0]["word"] == "specialization"
    assert len(res2[0]["phonemes"]) > 0


def test_pronunciation_scoring_pipelines():
    # Create 1.5 seconds of 16kHz audio buffer
    sr = 16000
    t = np.linspace(0, 1.5, int(sr * 1.5), endpoint=False)
    data = (np.sin(2 * np.pi * 300 * t) * 0.4).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="WAV")
    audio_bytes = buf.getvalue()

    # Test Whisper Simple Scoring
    simple_res = score_with_whisper(audio_bytes, "think")
    assert simple_res["method"] == "whisper"
    assert "accuracy_score" in simple_res
    assert "words" in simple_res

    # Test Wav2Vec2 Forced Alignment & GOP Scoring
    adv_res = score_with_wav2vec2_alignment(audio_bytes, "think", threshold=0.5)
    assert adv_res["method"] == "wav2vec2_gop"
    assert "overall_score" in adv_res
    assert len(adv_res["words"]) == 1
    w = adv_res["words"][0]
    assert w["word"] == "think"
    assert len(w["phonemes"]) == 4  # TH, IH, NG, K
    assert all("gop_score" in p for p in w["phonemes"])
    assert all("is_mispronounced" in p for p in w["phonemes"])


def test_pron_scoring_api():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r_g2p = client.post("/api/pron/g2p", json={"text": "think"})
    assert r_g2p.status_code == 200
    res_g2p = r_g2p.json()
    assert res_g2p[0]["word"] == "think"
    assert res_g2p[0]["arpabet"] == ["TH", "IH1", "NG", "K"]

    # Test scoring endpoint
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    data = (np.sin(2 * np.pi * 300 * t) * 0.4).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="WAV")

    r_score = client.post(
        "/api/pron/score",
        data={"target_text": "think", "method": "both", "threshold": "0.50"},
        files={"file": ("audio.wav", buf.getvalue(), "audio/wav")},
    )
    assert r_score.status_code == 200
    res = r_score.json()
    assert "simple" in res
    assert "advanced" in res
    assert "overall_score" in res
