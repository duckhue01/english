"""Pronunciation Scoring Engine:
1. G2P conversion: target text -> ARPAbet -> IPA (e.g., "think" -> /θɪŋk/).
2. Force-alignment: PyTorch Wav2Vec2 Forced Alignment (aligns audio to target sequence).
3. Scoring:
   - Simple: Whisper transcription + string alignment (Word Accuracy).
   - Advanced: Acoustic confidence / GOP (Goodness of Pronunciation) per phoneme.
"""

from __future__ import annotations

import io
import re
import ssl
from functools import lru_cache
from typing import Any

import g2p_en
import numpy as np
import soundfile as sf
import torch
import torchaudio.functional as F
import torchaudio.pipelines as pipelines

from app.pron.phonemes import is_vowel, split_stress, to_ipa

# Ensure SSL certificates verify properly for model downloading
try:
    import certifi
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

# Phonetic correction tips for commonly mispronounced American English sounds
PHONEME_TIPS: dict[str, str] = {
    "TH": "Voiceless dental fricative /θ/: Place the tip of your tongue lightly between your teeth and exhale without vibration (as in 'think', 'math').",
    "DH": "Voiced dental fricative /ð/: Place tongue tip between teeth and vibrate your vocal cords (as in 'this', 'weather').",
    "R": "American /r/ /ɹ/: Pull the tongue body back into the palate with curled or bunched edges without tapping the roof of the mouth.",
    "L": "Dark /l/ /ɫ/: Elevate the back of the tongue toward the soft palate (as in 'full', 'milk').",
    "IH": "Lax vowel /ɪ/: Relax your tongue and lips slightly lower and more central than /i/ (as in 'sit', 'think').",
    "IY": "Tense vowel /i/: Spread lips wide and position the tongue high and forward (as in 'seat', 'unique').",
    "AE": "Open front vowel /æ/: Drop your jaw low and spread lips wide (as in 'cat', 'black').",
    "V": "Voiced labiodental /v/: Press top teeth gently against lower lip and voice your sound.",
    "W": "Voiced velar glide /w/: Round lips tightly like sipping through a straw.",
    "NG": "Velar nasal /ŋ/: Raise the back of the tongue against the soft palate; air resonates through the nose (as in 'sing', 'think').",
    "SH": "Voiceless postalveolar /ʃ/: Round lips slightly, blade of tongue near alveolar ridge (as in 'ship').",
    "CH": "Affricate /tʃ/: Stop air with tongue at alveolar ridge then release into a fricative (as in 'chair').",
    "JH": "Voiced affricate /dʒ/: Voiced counterpart of /tʃ/ (as in 'judge', 'job').",
}


@lru_cache(maxsize=1)
def get_g2p_model() -> g2p_en.G2p:
    return g2p_en.G2p()


@lru_cache(maxsize=1)
def get_wav2vec2_bundle():
    bundle = pipelines.WAV2VEC2_ASR_BASE_960H
    model = bundle.get_model()
    model.eval()
    return bundle, model


@lru_cache(maxsize=1)
def get_whisper_model():
    import whisper
    return whisper.load_model("tiny.en")


def text_to_phonemes_ipa(text: str) -> list[dict[str, Any]]:
    """Convert original text to phonemes and IPA using g2p_en.
    e.g., 'think' -> ['TH', 'IH1', 'NG', 'K'] -> '/θɪŋk/'
    """
    g2p = get_g2p_model()
    words = re.findall(r"\b[A-Za-z0-9']+\b", text)
    results = []

    for w in words:
        raw_phones = [p for p in g2p(w) if p.strip()]
        phones_data = []
        ipa_parts = []

        for p in raw_phones:
            base, stress = split_stress(p)
            ph_ipa = to_ipa(p)
            stress_mark = "ˈ" if stress == 1 else ("ˌ" if stress == 2 else "")

            phones_data.append({
                "arpabet": p,
                "base": base,
                "stress": stress,
                "ipa": ph_ipa,
                "is_vowel": is_vowel(p),
                "tip": PHONEME_TIPS.get(base, ""),
            })

            if stress == 1:
                ipa_parts.append("ˈ" + ph_ipa)
            elif stress == 2:
                ipa_parts.append("ˌ" + ph_ipa)
            else:
                ipa_parts.append(ph_ipa)

        word_ipa = "/" + "".join(ipa_parts) + "/"

        results.append({
            "word": w,
            "arpabet": raw_phones,
            "ipa": word_ipa,
            "phonemes": phones_data,
        })

    return results


def load_audio_from_bytes(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    """Read in-memory audio bytes into 16kHz mono float32 numpy array."""
    buf = io.BytesIO(audio_bytes)
    data, sr = sf.read(buf, dtype="float32")

    # Convert to mono if stereo
    if data.ndim > 1:
        data = data.mean(axis=1)

    # Resample to 16000Hz if needed
    if sr != 16000:
        tensor = torch.from_numpy(data).unsqueeze(0)
        resampled = F.resample(tensor, orig_freq=sr, new_freq=16000)
        data = resampled.squeeze(0).numpy()
        sr = 16000

    return data, sr


def score_with_whisper(audio_bytes: bytes, target_text: str) -> dict[str, Any]:
    """Simple Approach:
    Transcribe recorded audio with Whisper -> compute word accuracy score against target text.
    """
    audio_arr, _ = load_audio_from_bytes(audio_bytes)
    model = get_whisper_model()

    res = model.transcribe(audio_arr, fp16=False, language="en")
    recognized_text = res.get("text", "").strip()

    def _clean_tokens(s: str) -> list[str]:
        return [w.lower() for w in re.findall(r"\b\w+\b", s)]

    target_tokens = _clean_tokens(target_text)
    spoken_tokens = _clean_tokens(recognized_text)

    # Dynamic programming string alignment (Needleman-Wunsch / Levenshtein word alignment)
    n = len(target_tokens)
    m = len(spoken_tokens)
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if target_tokens[i - 1] == spoken_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j - 1],  # substitution
                    dp[i - 1][j],      # deletion (omitted)
                    dp[i][j - 1],      # insertion (extra)
                )

    # Backtrack alignment path
    i, j = n, m
    aligned_words = []
    correct_count = 0

    while i > 0 or j > 0:
        if i > 0 and j > 0 and target_tokens[i - 1] == spoken_tokens[j - 1]:
            aligned_words.append({
                "target": target_tokens[i - 1],
                "spoken": spoken_tokens[j - 1],
                "status": "correct",
            })
            correct_count += 1
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            aligned_words.append({
                "target": target_tokens[i - 1],
                "spoken": spoken_tokens[j - 1],
                "status": "substituted",
            })
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            aligned_words.append({
                "target": target_tokens[i - 1],
                "spoken": "",
                "status": "omitted",
            })
            i -= 1
        else:
            aligned_words.append({
                "target": "",
                "spoken": spoken_tokens[j - 1],
                "status": "inserted",
            })
            j -= 1

    aligned_words.reverse()

    word_accuracy = round((correct_count / max(n, 1)) * 100, 1)
    edit_dist = dp[n][m]
    wer = round(edit_dist / max(n, 1), 2)

    return {
        "method": "whisper",
        "accuracy_score": word_accuracy,
        "word_error_rate": wer,
        "recognized_text": recognized_text,
        "target_text": target_text,
        "words": aligned_words,
    }


def score_with_wav2vec2_alignment(
    audio_bytes: bytes, target_text: str, threshold: float = 0.50
) -> dict[str, Any]:
    """Advanced Approach:
    Force-align recorded audio with PyTorch Wav2Vec2 Forced Alignment.
    Calculate acoustic confidence / GOP scores per phoneme -> flag phonemes below threshold.
    """
    audio_arr, sr = load_audio_from_bytes(audio_bytes)
    bundle, model = get_wav2vec2_bundle()
    labels = bundle.get_labels()
    dictionary = {c: i for i, c in enumerate(labels)}

    waveform = torch.from_numpy(audio_arr).unsqueeze(0)
    with torch.inference_mode():
        emissions, _ = model(waveform)
        emissions = torch.log_softmax(emissions, dim=-1)

    # Phonemize target text
    word_phonemes = text_to_phonemes_ipa(target_text)

    # Build character target sequence for alignment (Wav2Vec2 960h uses character CTC)
    clean_target = re.sub(r"[^A-Za-z\s']", "", target_text.upper()).strip()
    char_tokens = [dictionary[c] for c in clean_target if c in dictionary]

    if not char_tokens or emissions.size(1) < len(char_tokens):
        # Fallback if audio too short or empty
        return {
            "method": "wav2vec2_gop",
            "overall_score": 0.0,
            "threshold": threshold,
            "words": [],
            "error": "Audio duration too short for target text alignment",
        }

    targets = torch.tensor([char_tokens], dtype=torch.int32)
    aligned_tokens, scores = F.forced_align(emissions, targets, blank=0)
    spans = F.merge_tokens(aligned_tokens[0], scores[0], blank=0)

    # Calculate frame duration in seconds
    num_frames = emissions.size(1)
    audio_duration = audio_arr.shape[0] / sr
    sec_per_frame = audio_duration / max(num_frames, 1)

    # Map aligned character spans back to words and phonemes
    span_idx = 0
    scored_words = []
    all_phoneme_scores: list[float] = []

    for wp in word_phonemes:
        w_text = wp["word"].upper()
        # Find spans matching characters of this word
        w_spans = []
        for ch in w_text:
            if ch in dictionary and span_idx < len(spans):
                w_spans.append(spans[span_idx])
                span_idx += 1

        # Calculate word confidence and distribute across phonemes
        if w_spans:
            char_probs = [float(torch.exp(torch.tensor(s.score)).item()) for s in w_spans]
            w_score = float(np.mean(char_probs))
            w_start = round(w_spans[0].start * sec_per_frame, 3)
            w_end = round(w_spans[-1].end * sec_per_frame, 3)
        else:
            w_score = 0.0
            w_start = 0.0
            w_end = 0.0

        # Score individual phonemes with acoustic confidence (GOP proxy)
        phonemes_out = []
        num_phones = max(len(wp["phonemes"]), 1)
        for pi, ph in enumerate(wp["phonemes"]):
            # Associate each phoneme with proportionate temporal acoustic confidence
            if w_spans:
                p_span_idx = min(int((pi / num_phones) * len(w_spans)), len(w_spans) - 1)
                p_span = w_spans[p_span_idx]
                gop = float(torch.exp(torch.tensor(p_span.score)).item())
                p_start = round(p_span.start * sec_per_frame, 3)
                p_end = round(p_span.end * sec_per_frame, 3)
            else:
                gop = 0.0
                p_start = 0.0
                p_end = 0.0

            is_mispronounced = gop < threshold
            all_phoneme_scores.append(gop)

            phonemes_out.append({
                "arpabet": ph["arpabet"],
                "ipa": ph["ipa"],
                "stress": ph["stress"],
                "gop_score": round(gop, 3),
                "is_mispronounced": is_mispronounced,
                "start_time": p_start,
                "end_time": p_end,
                "tip": ph["tip"] if is_mispronounced else "",
            })

        scored_words.append({
            "word": wp["word"],
            "ipa": wp["ipa"],
            "score": round(w_score, 3),
            "is_mispronounced": any(p["is_mispronounced"] for p in phonemes_out),
            "start_time": w_start,
            "end_time": w_end,
            "phonemes": phonemes_out,
        })

    overall_score = round(float(np.mean(all_phoneme_scores)) * 100, 1) if all_phoneme_scores else 0.0

    return {
        "method": "wav2vec2_gop",
        "overall_score": overall_score,
        "threshold": threshold,
        "words": scored_words,
        "target_text": target_text,
    }


def evaluate_pronunciation(
    audio_bytes: bytes, target_text: str, threshold: float = 0.50
) -> dict[str, Any]:
    """Combines Simple (Whisper Word Accuracy) & Advanced (Wav2Vec2 GOP Phoneme Acoustic) scoring."""
    simple = score_with_whisper(audio_bytes, target_text)
    advanced = score_with_wav2vec2_alignment(audio_bytes, target_text, threshold=threshold)

    return {
        "simple": simple,
        "advanced": advanced,
        "overall_score": round((simple["accuracy_score"] * 0.4) + (advanced["overall_score"] * 0.6), 1),
    }
