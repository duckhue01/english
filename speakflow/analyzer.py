"""
Phonetic Analysis, IPA Transcription, and Real-Time Feedback Engine for SpeakFlow.
Provides instant syllable stress breakdown, mouth/tongue tips, and acoustic pacing audits.
"""

import re
from typing import List, Dict, Any, Tuple
import numpy as np
import eng_to_ipa as ipa
import pronouncing
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED, HEAVY, SIMPLE

console = Console()


def get_word_stress_visual(phones: List[str]) -> Tuple[str, str]:
    """
    Format syllable stress into visual dot badges and phonetic representations.
    Example: 100 -> '[● ○ ○]', 'SCAR-ci-ty'
    """
    stresses = pronouncing.stresses(" ".join(phones))
    if not stresses:
        return "[○]", ""

    dots = []
    for s in stresses:
        if s == "1":
            dots.append("●")  # Primary stress
        elif s == "2":
            dots.append("◐")  # Secondary stress
        else:
            dots.append("○")  # Unstressed

    visual = f"[{' '.join(dots)}]"
    return visual, stresses


def detect_phonetic_tips(word: str, ipa_str: str, phones: List[str]) -> List[str]:
    """
    Detect specific pronunciation pitfalls and generate physical mouth/tongue articulation tips.
    """
    tips = []
    w_lower = word.lower()

    # S-blend pitfalls (scarcity, study, stay, school)
    if re.match(r"^(sc|sk|sp|st|sm|sn|sl|sw)", w_lower):
        tips.append("S-Cluster: Start directly with a crisp hiss without prepending an extra vowel (avoid 'es-scarcity' or 'es-study').")

    # Soft C followed by e, i, y (scarcity, city) - exclude 'ch'
    if re.search(r"(?<!h)c[eiy]", w_lower) and not w_lower.startswith("ch"):
        tips.append("Soft 'c': Articulate as /s/ (tongue near alveolar ridge, light hiss), not hard /k/.")

    # CH /tʃ/ affricate (choices, check, chair)
    if "ch" in w_lower or "ʧ" in ipa_str:
        tips.append("CH (/tʃ/): Press tongue tip to alveolar ridge to stop airflow, then release with explosive 'sh'.")

    # Diphthong /ɔɪ/ (choices, voice, boy)
    if "oi" in w_lower or "oy" in w_lower or "ɔɪ" in ipa_str:
        tips.append("Diphthong /ɔɪ/: Start with rounded lips for 'aw' (/ɔ/) and smoothly glide into an unrounded smile 'ee' (/ɪ/).")

    # Plural or third person -es / -s ending (choices, boxes)
    if w_lower.endswith(("ces", "ses", "xes", "ches", "shes", "zes")):
        tips.append("Ending '-es': Pronounce as a full voiced syllable /-ɪz/ (with a buzzy 'z'), not a flat 's'.")

    # Short /ʌ/ vs /ə/ (study)
    if "u" in w_lower and "ə" in ipa_str or "ʌ" in ipa_str:
        tips.append("Vowel /ʌ/: Keep tongue relaxed and low in the center of the mouth with jaw dropped slightly.")

    # Flap T in American English (scarcity -> [ˈskɛrsɪɾi], butter, city)
    if "t" in w_lower and len(phones) > 3:
        tips.append("American Flap-T: The 't' between vowels can be lightly tapped against the upper gum ridge like a quick /d/.")

    return tips


def detect_connected_speech(words: List[str]) -> List[str]:
    """
    Analyze transitions between adjacent words to highlight linking and reduction opportunities.
    """
    linking = []
    for i in range(len(words) - 1):
        w1 = words[i].strip(".,!?;:").lower()
        w2 = words[i + 1].strip(".,!?;:").lower()

        # Vowel-to-vowel glide insertion (e.g. "Study of" -> /i/ + /ə/ = [di-j-əv])
        if w1.endswith(("y", "ie", "ee", "e")) and w2.startswith(("a", "e", "i", "o", "u")):
            linking.append(f"🔗 Vowel Glide: '{w1}' ends in /i/ and '{w2}' starts with a vowel -> insert a smooth /j/ glide: [{w1}‿j‿{w2}]")

        # Function word reduction: "and" -> [ən]
        if w2 == "and":
            linking.append(f"📉 Reduction: 'and' typically reduces from /ænd/ to weak form /ən/ or /ənd/ in natural speech.")

        # Consonant-to-vowel linking (e.g. "and choices" or "choices and")
        if not w1.endswith(("a", "e", "i", "o", "u", "y")) and w2.startswith(("a", "e", "i", "o", "u")):
            linking.append(f"🔗 Consonant-to-Vowel: Link final consonant of '{w1}' into initial vowel of '{w2}'.")

    return linking


def analyze_phrase_phonetics(phrase: str) -> Dict[str, Any]:
    """
    Complete phonetic breakdown of a target phrase including full IPA,
    word-by-word stress, phoneme pitfalls, and connected speech cues.
    """
    clean_phrase = phrase.strip()
    words = clean_phrase.split()
    full_ipa = ipa.convert(clean_phrase)

    word_cards = []
    for w in words:
        clean_w = re.sub(r"[^\w]", "", w).lower()
        w_ipa = ipa.convert(clean_w)
        phones_list = pronouncing.phones_for_word(clean_w)

        if phones_list:
            phones = phones_list[0].split()
            stress_visual, stress_seq = get_word_stress_visual(phones)
            syl_count = pronouncing.syllable_count(phones_list[0])
            rhymes = pronouncing.rhymes(clean_w)[:3]
        else:
            phones = []
            stress_visual = "[●]"
            stress_seq = "1"
            syl_count = 1
            rhymes = []

        tips = detect_phonetic_tips(clean_w, w_ipa, phones)

        word_cards.append({
            "word": w,
            "clean": clean_w,
            "ipa": w_ipa,
            "syllables": syl_count,
            "stress_visual": stress_visual,
            "stress_seq": stress_seq,
            "phones": phones,
            "rhymes": rhymes,
            "tips": tips,
        })

    connected_cues = detect_connected_speech(words)

    return {
        "phrase": clean_phrase,
        "full_ipa": full_ipa,
        "word_count": len(words),
        "word_cards": word_cards,
        "connected_cues": connected_cues,
    }


def analyze_speech_acoustics(
    audio_data: np.ndarray,
    samplerate: int,
    target_phrase: str,
) -> Dict[str, Any]:
    """
    Analyze spoken acoustic metrics: duration, speaking pace (WPM),
    speech-to-silence ratio, dynamic expressiveness, and rhythmic cadence.
    """
    total_sec = len(audio_data) / samplerate
    words = target_phrase.split()
    word_count = len(words)

    # Frame energy analysis (25ms frames)
    frame_len = int(0.025 * samplerate)
    hop_len = int(0.010 * samplerate)
    n_frames = max(1, (len(audio_data) - frame_len) // hop_len)

    energies = []
    for i in range(n_frames):
        chunk = audio_data[i * hop_len : i * hop_len + frame_len]
        rms = np.sqrt(np.mean(chunk ** 2))
        energies.append(rms)

    energies = np.array(energies)
    speech_thresh = np.percentile(energies, 30) if len(energies) > 0 else 0.01
    active_frames = np.sum(energies > max(0.005, speech_thresh))
    active_speech_sec = (active_frames * hop_len) / samplerate

    # Words Per Minute (WPM)
    wpm = (word_count / max(0.4, total_sec)) * 60.0

    # Rate pacing
    if wpm < 90:
        pacing_grade = "Deliberate / Slow"
        pacing_badge = "[yellow]Slow Pacing (Clear for Drills)[/yellow]"
        pacing_tip = "You spoke with careful deliberation. Try increasing tempo slightly for natural conversation."
    elif 90 <= wpm <= 165:
        pacing_grade = "Ideal Natural Cadence"
        pacing_badge = "[bold green]Ideal Cadence (110-150 WPM)[/bold green]"
        pacing_tip = "Outstanding tempo! You allowed enough time for clear vowel articulation without rushing."
    else:
        pacing_grade = "Rushed / Fast"
        pacing_badge = "[bold red]Fast / Rushed Pace (> 165 WPM)[/bold red]"
        pacing_tip = "Speech rate was slightly rushed. Slow down on multisyllabic words to enunciate consonants."

    # Dynamic emphasis / Intonation contour variation
    std_energy = np.std(energies) if len(energies) > 0 else 0.0
    crest_factor = (np.max(energies) / max(1e-5, np.mean(energies))) if len(energies) > 0 else 1.0

    if crest_factor > 2.5:
        expressiveness = "Dynamic Sentence Stress"
        rhythm_score = min(10.0, 8.5 + min(1.5, (crest_factor - 2.5) * 0.4))
        rhythm_note = "Great vocal inflection! You placed clear emphasis on key content words."
    else:
        expressiveness = "Even / Level Inflection"
        rhythm_score = 7.5
        rhythm_note = "Your pitch was fairly even. Make sure to punch the stressed syllables in key nouns."

    return {
        "total_sec": total_sec,
        "active_speech_sec": active_speech_sec,
        "word_count": word_count,
        "wpm": round(wpm, 1),
        "pacing_grade": pacing_grade,
        "pacing_badge": pacing_badge,
        "pacing_tip": pacing_tip,
        "expressiveness": expressiveness,
        "rhythm_score": round(rhythm_score, 1),
        "rhythm_note": rhythm_note,
    }


def render_phrase_coaching_card(analysis: Dict[str, Any]) -> Panel:
    """
    Render a comprehensive terminal coaching panel with IPA,
    syllable stress visualization, and mouth placement tips.
    """
    content = Text()
    content.append("🎯 Practice Phrase:\n", style="bold yellow")
    content.append(f'"{analysis["phrase"]}"\n\n', style="bold bright_white")

    content.append("🔤 Target IPA Pronunciation:\n", style="bold cyan")
    content.append(f"/{analysis['full_ipa']}/\n\n", style="bold bright_cyan on black")

    # Word-by-word table
    table = Table(box=SIMPLE, expand=True, padding=(0, 1), show_edge=False)
    table.add_column("Word", style="bold bright_white", width=14)
    table.add_column("Target IPA", style="cyan", width=16)
    table.add_column("Stress", justify="center", style="yellow", width=12)
    table.add_column("Key Articulation Tip", style="bright_black")

    for card in analysis["word_cards"]:
        primary_tip = card["tips"][0] if card["tips"] else "Clear vowel articulation"
        table.add_row(
            card["word"],
            f"/{card['ipa']}/",
            card["stress_visual"],
            primary_tip,
        )

    # Connected speech block
    if analysis["connected_cues"]:
        linking_text = "\n".join(f"• {cue}" for cue in analysis["connected_cues"])
    else:
        linking_text = "• Maintain continuous breath flow between words without hard glottal stops."

    grid = Table.grid(expand=True)
    grid.add_column()
    grid.add_row(content)
    grid.add_row(table)
    grid.add_row(Text(f"\n🌊 Connected Speech & Linking Flow:\n{linking_text}\n", style="dim yellow"))

    return Panel(
        grid,
        title="[bold green]PHRASE PRONUNCIATION LAB (IPA & COACHING)[/bold green]",
        border_style="cyan",
        box=ROUNDED,
        padding=(1, 2),
    )


def render_realtime_feedback_card(
    analysis: Dict[str, Any],
    acoustics: Dict[str, Any],
) -> Panel:
    """
    Render instant post-recording acoustic & pacing feedback.
    """
    grid = Table.grid(expand=True)
    grid.add_column()

    header = Text()
    header.append("📊 REAL-TIME RECORDING AUDIT\n", style="bold cyan")
    header.append(f"Phrase: \"{analysis['phrase']}\"  •  Duration: {acoustics['total_sec']:.1f}s  •  Pacing: {acoustics['wpm']} WPM\n", style="dim")

    # Metrics Grid
    table = Table(box=ROUNDED, expand=True, border_style="dim")
    table.add_column("Metric", style="bold white")
    table.add_column("Your Result", style="bright_cyan")
    table.add_column("Benchmark & Diagnostic Tip", style="dim")

    table.add_row(
        "Tempo / Pacing",
        f"{acoustics['wpm']} WPM",
        acoustics["pacing_badge"],
    )
    table.add_row(
        "Rhythm & Stress",
        f"{acoustics['rhythm_score']} / 10",
        acoustics["rhythm_note"],
    )
    table.add_row(
        "Target Phonetics",
        f"/{analysis['full_ipa']}/",
        f"{len(analysis['word_cards'])} words analyzed",
    )

    # Actionable Tips block
    tips_text = Text()
    tips_text.append("\n💡 Tailored Articulation Drills for this phrase:\n", style="bold yellow")
    for card in analysis["word_cards"]:
        if card["tips"]:
            tips_text.append(f"• [bold white]{card['word']}[/bold white] (/{card['ipa']}/): {card['tips'][0]}\n", style="bright_white")

    grid.add_row(header)
    grid.add_row(table)
    grid.add_row(tips_text)

    return Panel(
        grid,
        title="[bold green]INSTANT PRONUNCIATION FEEDBACK[/bold green]",
        border_style="green",
        box=HEAVY,
        padding=(1, 2),
    )
