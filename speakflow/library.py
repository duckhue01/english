"""
Curated Practice Library for SpeakFlow.
Contains targeted pronunciation exercises, phoneme drills, tongue twisters,
and real-world speaking scripts.
"""

from typing import List, Dict, Any

PRACTICE_LIBRARY: List[Dict[str, Any]] = [
    # Category: Tricky Phonemes
    {
        "id": "th_sounds",
        "category": "Tricky Phonemes",
        "title": "The Voiced & Voiceless 'TH' (/θ/ and /ð/)",
        "difficulty": "Intermediate",
        "focus": (
            "- Voiceless /θ/: 'thought', 'thirty', 'thousand', 'feathers', 'breath'\n"
            "- Voiced /ð/: 'the', 'their', 'brother', 'breathe', 'smooth'\n"
            "- Tip: Ensure the tongue tip gently protrudes between your upper and lower incisors without biting down."
        ),
        "text": (
            "The thought of thirty-three thousand feathers tickling their throats made both brothers laugh. "
            "Although the weather was rather chilly, they walked together through the thick brush, "
            "breathing the healthy, southern breeze without another thought."
        ),
    },
    {
        "id": "r_vs_l",
        "category": "Tricky Phonemes",
        "title": "The 'R' vs 'L' Liquid Distinction (/r/ vs /l/)",
        "difficulty": "Intermediate",
        "focus": (
            "- English /r/: Tongue curls back or bunches without touching the roof of the mouth.\n"
            "- English /l/: Tongue tip presses firmly against the alveolar ridge behind front teeth.\n"
            "- Minimal pairs: 'royal' vs 'loyal', 'really' vs 'rural', 'light' vs 'right'."
        ),
        "text": (
            "Really rural roads rarely relieve weary travelers who roll leisurely along the river. "
            "Larry and Rory realized that loyalty requires real reliability, "
            "so they looked left and right before rolling rapidly down the long, rocky lane."
        ),
    },
    {
        "id": "v_vs_w",
        "category": "Tricky Phonemes",
        "title": "The 'V' vs 'W' Contrast (/v/ vs /w/)",
        "difficulty": "Beginner",
        "focus": (
            "- Labiodental /v/: Upper teeth touch lower lip with vocal cord vibration.\n"
            "- Bilabial /w/: Both lips round tightly like a whistle with no teeth contact.\n"
            "- Contrast words: 'vest' vs 'west', 'vivid' vs 'window', 'very' vs 'wary'."
        ),
        "text": (
            "Very wary wolves wander through the vivid valley while warm winter winds blow from the west. "
            "Victor viewed the vast wilderness from the wooden window and wondered whatever would happen to the village."
        ),
    },
    {
        "id": "past_tense_ed",
        "category": "Tricky Phonemes",
        "title": "Past Tense '-ed' Endings (/t/, /d/, and /ɪd/)",
        "difficulty": "Intermediate",
        "focus": (
            "- /t/ after voiceless consonants: walked, laughed, stopped, passed.\n"
            "- /d/ after voiced sounds: lived, played, seemed, opened.\n"
            "- /ɪd/ after 't' or 'd' sounds: decided, waited, needed, painted.\n"
            "- Do not add extra syllables to words like 'walked' or 'laughed'!"
        ),
        "text": (
            "Yesterday, Sarah walked into the studio, laughed at the funny poster, and stopped to listen. "
            "She decided that she needed more practice, so she painted a fresh sign and waited for her friends. "
            "They arrived early, played great music, and opened everyone's hearts."
        ),
    },
    {
        "id": "vowel_ship_sheep",
        "category": "Tricky Phonemes",
        "title": "Short /ɪ/ vs Long /iː/ (Ship vs Sheep)",
        "difficulty": "Intermediate",
        "focus": (
            "- Lax /ɪ/: 'sit', 'hit', 'live', 'fill', 'bitch/beach contrast'. Tongue is relaxed.\n"
            "- Tense /iː/: 'seat', 'heat', 'leave', 'feel'. Tongue is high and lips spread into a slight smile."
        ),
        "text": (
            "Please take a seat and sit quietly while we review the list. "
            "He will leave the keys if you live near the green field. "
            "The captain looked out from the great ship and saw six white sheep grazing beside the deep sea."
        ),
    },

    # Category: Connected Speech & Rhythm
    {
        "id": "connected_speech_reductions",
        "category": "Connected Speech & Rhythm",
        "title": "Linking, Reductions & Flap-T",
        "difficulty": "Advanced",
        "focus": (
            "- Flap 'T' between vowels: 'water' -> [wah-der], 'better' -> [beh-der], 'city' -> [sih-dee].\n"
            "- Contractions & Reductions: 'going to' -> 'gonna', 'want to' -> 'wanna', 'could have' -> 'coulda'.\n"
            "- Consonant-to-vowel linking: 'hold on' -> [hol-don], 'check it out' -> [che-ki-tout]."
        ),
        "text": (
            "What are you going to do about the meeting later today? "
            "I could have sworn we decided to hold on until next Wednesday. "
            "If you want to grab a better bottle of water in the city, check it out right across the street."
        ),
    },
    {
        "id": "sentence_stress_meaning",
        "category": "Connected Speech & Rhythm",
        "title": "Sentence Stress & Pitch Shifts",
        "difficulty": "Advanced",
        "focus": (
            "- English is a stress-timed language.\n"
            "- Content words (nouns, main verbs, adjectives) carry stress; function words (prepositions, articles) shrink to schwa /ə/.\n"
            "- Notice how shifting emphasis changes meaning."
        ),
        "text": (
            "I never said she stole my money, but someone definitely took something from that desk. "
            "If we want real progress, we have to commit to consistent daily habits rather than occasional bursts of effort."
        ),
    },

    # Category: Tongue Twisters & Warmups
    {
        "id": "twister_peter_piper",
        "category": "Tongue Twisters",
        "title": "Peter Piper's Pickled Peppers (Plosive /p/)",
        "difficulty": "Beginner",
        "focus": (
            "- Crisp bilabial plosive /p/ with a burst of air (aspiration).\n"
            "- Keep vowels distinct and tempo steady before speeding up."
        ),
        "text": (
            "Peter Piper picked a peck of pickled peppers. "
            "A peck of pickled peppers Peter Piper picked. "
            "If Peter Piper picked a peck of pickled peppers, "
            "where's the peck of pickled peppers Peter Piper picked?"
        ),
    },
    {
        "id": "twister_betty_botter",
        "category": "Tongue Twisters",
        "title": "Betty Botter's Butter (Voiced Plosive /b/ & Flap-T)",
        "difficulty": "Intermediate",
        "focus": (
            "- Rapid alternation between /b/, /t/, and vowel heights.\n"
            "- Work on American flap-T: 'butter' [bʌdər], 'bitter' [bɪdər], 'batter' [bædər]."
        ),
        "text": (
            "Betty Botter bought some butter, but she said the butter's bitter. "
            "If I put it in my batter, it will make my batter bitter. "
            "So she bought a bit of butter better than her bitter butter, "
            "and she baked it in her batter, and the batter was not bitter!"
        ),
    },
    {
        "id": "twister_seashells",
        "category": "Tongue Twisters",
        "title": "She Sells Seashells (Sibilants /s/ vs /ʃ/)",
        "difficulty": "Intermediate",
        "focus": (
            "- Alveolar /s/ (sharp hiss, tongue behind upper teeth) vs Post-alveolar /ʃ/ ('sh', lips flared slightly, tongue pulled back)."
        ),
        "text": (
            "She sells seashells by the seashore. "
            "The shells she sells are surely seashells. "
            "So if she sells shells on the seashore, "
            "I'm sure she sells seashore shells."
        ),
    },

    # Category: Professional & Workplace
    {
        "id": "elevator_pitch",
        "category": "Professional & Workplace",
        "title": "The 30-Second Executive Pitch",
        "difficulty": "Intermediate",
        "focus": (
            "- Confident downward inflection at the end of statements.\n"
            "- Controlled pacing: 130-150 words per minute.\n"
            "- Highlighting key nouns: 'platform', 'efficiency', 'scalable', 'results'."
        ),
        "text": (
            "Hi everyone, thanks for joining today. "
            "We are building an intelligent workflow engine that streamlines complex data pipelines in real time. "
            "By replacing manual handoffs with automated intelligence, our customers cut turnaround times by sixty percent "
            "while significantly reducing operational costs. Let's dive right into the demonstration."
        ),
    },
    {
        "id": "standup_update",
        "category": "Professional & Workplace",
        "title": "Daily Agile Standup Update",
        "difficulty": "Beginner",
        "focus": (
            "- Natural conversational flow, clear past and future verb tenses.\n"
            "- Technical vocabulary articulation: 'architecture', 'refactored', 'deployment'."
        ),
        "text": (
            "Yesterday, I finished refactoring the authentication middleware and merged the PR into main. "
            "Today, I'm focusing on improving query performance across the dashboard APIs. "
            "I don't have any blockers right now, but I would appreciate a quick code review from someone on the core team before lunch."
        ),
    },

    # Category: IELTS / TOEFL Speaking
    {
        "id": "ielts_cue_card_journey",
        "category": "IELTS & Academic",
        "title": "IELTS Part 2: A Memorable Journey",
        "difficulty": "Advanced",
        "focus": (
            "- Descriptive adjectives, natural rhythm, expressive pauses at clause boundaries.\n"
            "- Avoiding monotone delivery and filler sounds (um, uh, like)."
        ),
        "text": (
            "One of the most memorable trips I have ever taken was a train ride through the northern highlands. "
            "The scenery was absolutely breathtaking, with misty mountain peaks towering above emerald green valleys. "
            "What stood out most was how welcoming the local residents were whenever we stopped at small rural stations. "
            "It gave me a fresh perspective on how rewarding travel can truly be."
        ),
    },
    {
        "id": "toefl_technology_opinion",
        "category": "IELTS & Academic",
        "title": "TOEFL Academic: Technology & Human Connection",
        "difficulty": "Advanced",
        "focus": (
            "- Formal academic discourse, transitional signposts ('Furthermore', 'On the contrary', 'Consequently').\n"
            "- Clear syllable stress on multisyllabic academic words."
        ),
        "text": (
            "While critics often argue that modern digital devices isolate individuals from tangible community interactions, "
            "I believe technology ultimately bridges geographical divides. "
            "Collaborative platforms enable international scholars to exchange ideas instantly and seamlessly. "
            "Consequently, global communication has become substantially more inclusive and democratic than ever before."
        ),
    },
]


def get_categories() -> List[str]:
    """Return all unique categories in the library."""
    cats = []
    for item in PRACTICE_LIBRARY:
        if item["category"] not in cats:
            cats.append(item["category"])
    return cats


def get_items_by_category(category: str) -> List[Dict[str, Any]]:
    """Return practice items within a specific category."""
    return [item for item in PRACTICE_LIBRARY if item["category"] == category]


def get_item_by_id(item_id: str) -> Dict[str, Any]:
    """Retrieve a specific practice item by ID."""
    for item in PRACTICE_LIBRARY:
        if item["id"] == item_id:
            return item
    raise KeyError(f"Item with ID '{item_id}' not found.")
